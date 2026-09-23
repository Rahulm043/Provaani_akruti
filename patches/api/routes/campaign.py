import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import text

from api.constants import (
    DEFAULT_CAMPAIGN_RETRY_CONFIG,
    DEFAULT_ORG_CONCURRENCY_LIMIT,
)
from api.db import db_client
from api.db.models import UserModel
from api.enums import OrganizationConfigurationKey
from api.services.auth.depends import get_user
from api.services.campaign.runner import campaign_runner_service
from api.services.campaign.source_sync import CampaignSourceSyncService
from api.services.campaign.source_sync_factory import get_sync_service
from api.services.quota_service import authorize_workflow_run_start
from api.services.reports import generate_campaign_report_csv
from api.services.storage import storage_fs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaign")


async def _get_org_concurrent_limit(organization_id: int) -> int:
    """Get the concurrent call limit for an organization."""
    try:
        config = await db_client.get_configuration(
            organization_id,
            OrganizationConfigurationKey.CONCURRENT_CALL_LIMIT.value,
        )
        if config and config.value:
            return int(config.value.get("value", DEFAULT_ORG_CONCURRENCY_LIMIT))
    except Exception:
        pass
    return DEFAULT_ORG_CONCURRENCY_LIMIT


async def _get_from_numbers_count(organization_id: int) -> int:
    """Active phone-number count from the org's default telephony config.
    Used to validate ``max_concurrency`` against caller-id supply.

    PATCHED: Return a high value so concurrency is limited only by
    org_limit, not by the number of configured phone numbers.
    A single Plivo number supports multiple concurrent calls.
    """
    try:
        default_cfg = await db_client.get_default_telephony_configuration(
            organization_id
        )
        if default_cfg:
            addresses = await db_client.list_active_normalized_addresses_for_config(
                default_cfg.id
            )
            return max(len(addresses), 100)
    except Exception:
        pass
    return 100


async def _validate_max_concurrency(max_concurrency: int, organization_id: int) -> None:
    """Validate max_concurrency against org limit and configured phone numbers.

    Raises HTTPException(400) if the value exceeds the effective limit.
    """
    org_limit = await _get_org_concurrent_limit(organization_id)
    from_numbers_count = await _get_from_numbers_count(organization_id)
    effective_limit = (
        min(org_limit, from_numbers_count) if from_numbers_count > 0 else org_limit
    )
    if max_concurrency > effective_limit:
        if from_numbers_count > 0 and from_numbers_count < org_limit:
            raise HTTPException(
                status_code=400,
                detail=f"max_concurrency ({max_concurrency}) cannot exceed {effective_limit}. You have {from_numbers_count} phone number(s) configured. Add more CLIs in telephony configuration to increase concurrency.",
            )
        raise HTTPException(
            status_code=400,
            detail=f"max_concurrency ({max_concurrency}) cannot exceed organization limit ({effective_limit})",
        )


class RetryConfigRequest(BaseModel):
    enabled: bool = True
    max_retries: int = Field(default=2, ge=0, le=10)
    retry_delay_seconds: int = Field(default=120, ge=30, le=3600)
    retry_on_busy: bool = True
    retry_on_no_answer: bool = True
    retry_on_voicemail: bool = True


class RetryConfigResponse(BaseModel):
    enabled: bool
    max_retries: int
    retry_delay_seconds: int
    retry_on_busy: bool
    retry_on_no_answer: bool
    retry_on_voicemail: bool


class TimeSlotRequest(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$")

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class ScheduleConfigRequest(BaseModel):
    enabled: bool = True
    timezone: str = "UTC"
    slots: List[TimeSlotRequest] = Field(..., min_length=1, max_length=50)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (KeyError, Exception):
            raise ValueError(f"Invalid timezone: {v}")
        return v


class TimeSlotResponse(BaseModel):
    day_of_week: int
    start_time: str
    end_time: str


class ScheduleConfigResponse(BaseModel):
    enabled: bool
    timezone: str
    slots: List[TimeSlotResponse]


class CircuitBreakerConfigRequest(BaseModel):
    enabled: bool = True
    failure_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    window_seconds: int = Field(default=120, ge=30, le=600)
    min_calls_in_window: int = Field(default=5, ge=1, le=100)


class CircuitBreakerConfigResponse(BaseModel):
    enabled: bool = False
    failure_threshold: float = 0.5
    window_seconds: int = 120
    min_calls_in_window: int = 5


class CreateCampaignRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    workflow_id: int
    source_type: str = Field(..., pattern="^csv$")
    source_id: str  # CSV file key
    # Optional during the legacy → multi-config migration window. Required in
    # a follow-up. When omitted, the dispatcher falls back to the org's
    # default config.
    telephony_configuration_id: Optional[int] = None
    retry_config: Optional[RetryConfigRequest] = None
    max_concurrency: Optional[int] = Field(default=None, ge=1, le=100)
    schedule_config: Optional[ScheduleConfigRequest] = None
    circuit_breaker: Optional[CircuitBreakerConfigRequest] = None


class UpdateCampaignRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    retry_config: Optional[RetryConfigRequest] = None
    max_concurrency: Optional[int] = Field(default=None, ge=1, le=100)
    schedule_config: Optional[ScheduleConfigRequest] = None
    circuit_breaker: Optional[CircuitBreakerConfigRequest] = None


class CampaignLogEntryResponse(BaseModel):
    """A single timestamped entry from the campaign's append-only log.

    Surfaced in the UI so operators can see why a campaign moved to
    paused / failed without digging through server logs.
    """

    ts: str
    level: str
    event: str
    message: str
    details: Optional[Dict[str, Any]] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    workflow_id: int
    workflow_name: str
    state: str
    source_type: str
    source_id: str
    total_rows: Optional[int]
    processed_rows: int
    failed_rows: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    retry_config: RetryConfigResponse
    max_concurrency: Optional[int] = None
    schedule_config: Optional[ScheduleConfigResponse] = None
    circuit_breaker: Optional[CircuitBreakerConfigResponse] = None
    executed_count: int = 0
    total_queued_count: int = 0
    parent_campaign_id: Optional[int] = None
    redialed_campaign_id: Optional[int] = None
    telephony_configuration_id: Optional[int] = None
    telephony_configuration_name: Optional[str] = None
    logs: List[CampaignLogEntryResponse] = Field(default_factory=list)


class CampaignsResponse(BaseModel):
    campaigns: List[CampaignResponse]


class WorkflowRunResponse(BaseModel):
    id: int
    workflow_id: int
    state: str
    created_at: datetime
    completed_at: Optional[datetime]


class CampaignRunsResponse(BaseModel):
    """Paginated response for campaign workflow runs"""

    runs: List[dict]  # WorkflowRunResponseSchema from schemas
    total_count: int
    page: int
    limit: int
    total_pages: int


class CampaignProgressResponse(BaseModel):
    campaign_id: int
    state: str
    total_rows: int
    processed_rows: int
    failed_calls: int
    progress_percentage: float
    source_sync: dict
    rate_limit: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


# Default retry config for campaigns


def _build_campaign_response(
    campaign,
    workflow_name: str,
    executed_count: int = 0,
    total_queued_count: int = 0,
    telephony_configuration_name: Optional[str] = None,
) -> CampaignResponse:
    """Build a CampaignResponse from a campaign model."""
    # Get retry_config from campaign or use defaults
    retry_config = (
        campaign.retry_config
        if campaign.retry_config
        else DEFAULT_CAMPAIGN_RETRY_CONFIG
    )

    # Get max_concurrency, schedule_config, circuit_breaker from orchestrator_metadata
    max_concurrency = None
    schedule_config = None
    circuit_breaker_config = CircuitBreakerConfigResponse()
    parent_campaign_id = None
    redialed_campaign_id = None
    if campaign.orchestrator_metadata:
        max_concurrency = campaign.orchestrator_metadata.get("max_concurrency")
        sc = campaign.orchestrator_metadata.get("schedule_config")
        if sc:
            schedule_config = ScheduleConfigResponse(
                enabled=sc.get("enabled", False),
                timezone=sc.get("timezone", "UTC"),
                slots=[TimeSlotResponse(**slot) for slot in sc.get("slots", [])],
            )
        cb = campaign.orchestrator_metadata.get("circuit_breaker")
        if cb:
            circuit_breaker_config = CircuitBreakerConfigResponse(**cb)
        parent_campaign_id = campaign.orchestrator_metadata.get("parent_campaign_id")
        redialed_campaign_id = campaign.orchestrator_metadata.get(
            "redialed_campaign_id"
        )

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        workflow_id=campaign.workflow_id,
        workflow_name=workflow_name,
        state=campaign.state,
        source_type=campaign.source_type,
        source_id=campaign.source_id,
        total_rows=campaign.total_rows,
        processed_rows=campaign.processed_rows,
        failed_rows=campaign.failed_rows,
        created_at=campaign.created_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        retry_config=RetryConfigResponse(**retry_config),
        max_concurrency=max_concurrency,
        schedule_config=schedule_config,
        circuit_breaker=circuit_breaker_config,
        executed_count=executed_count,
        total_queued_count=total_queued_count,
        parent_campaign_id=parent_campaign_id,
        redialed_campaign_id=redialed_campaign_id,
        telephony_configuration_id=campaign.telephony_configuration_id,
        telephony_configuration_name=telephony_configuration_name,
        logs=[
            CampaignLogEntryResponse(**entry)
            for entry in (campaign.logs or [])
            if isinstance(entry, dict)
        ],
    )


async def _get_campaign_stats(campaign_id: int) -> tuple[int, int]:
    """Return (executed_count, total_queued_count) for a campaign."""
    stats_map = await db_client.get_queued_runs_stats_for_campaigns([campaign_id])
    s = stats_map.get(campaign_id, {})
    return s.get("executed", 0), s.get("total", 0)


async def _get_telephony_configuration_name(
    config_id: Optional[int], organization_id: int
) -> Optional[str]:
    """Resolve the display name for a campaign's telephony configuration.

    Org-scoped lookup so a stale FK from another org (shouldn't happen, but
    cheap to enforce) doesn't leak across tenants.
    """
    if config_id is None:
        return None
    cfg = await db_client.get_telephony_configuration_for_org(
        config_id, organization_id
    )
    return cfg.name if cfg else None


@router.post("/create")
async def create_campaign(
    request: CreateCampaignRequest,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Create a new campaign"""
    # Verify workflow exists and belongs to organization
    workflow = await db_client.get_workflow(
        request.workflow_id, organization_id=user.selected_organization_id
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow_name = workflow.name

    # Validate source data (phone_number column and format)
    sync_service = get_sync_service(request.source_type)
    validation_result = await sync_service.validate_source(
        request.source_id, user.selected_organization_id
    )
    if not validation_result.is_valid:
        raise HTTPException(status_code=400, detail=validation_result.error.message)

    # Validate template variables against source data columns
    if workflow:
        from api.services.workflow.dto import ReactFlowDTO
        from api.services.workflow.workflow_graph import WorkflowGraph

        workflow_def = workflow.released_definition.workflow_json
        if workflow_def:
            try:
                dto = ReactFlowDTO(**workflow_def)
                graph = WorkflowGraph(dto, skip_instance_constraints_for={"trigger"})
                required_vars = graph.get_required_template_variables()

                if (
                    required_vars
                    and validation_result.headers
                    and validation_result.rows
                ):
                    template_validation = (
                        CampaignSourceSyncService.validate_template_columns(
                            validation_result.headers,
                            validation_result.rows,
                            required_vars,
                        )
                    )
                    if not template_validation.is_valid:
                        raise HTTPException(
                            status_code=400,
                            detail=template_validation.error.message,
                        )
            except HTTPException:
                raise
            except Exception:
                pass  # Don't block campaign creation if template extraction fails

    if request.max_concurrency is not None:
        await _validate_max_concurrency(
            request.max_concurrency, user.selected_organization_id
        )

    # Resolve which telephony config the campaign is pinned to. Explicit value
    # wins; otherwise default to the org's default config so legacy clients keep
    # working through the migration window.
    telephony_configuration_id = request.telephony_configuration_id
    if telephony_configuration_id:
        cfg = await db_client.get_telephony_configuration_for_org(
            telephony_configuration_id, user.selected_organization_id
        )
        if not cfg:
            raise HTTPException(
                status_code=400, detail="telephony_configuration_not_found"
            )
    else:
        default_cfg = await db_client.get_default_telephony_configuration(
            user.selected_organization_id
        )
        if default_cfg:
            telephony_configuration_id = default_cfg.id

    # Build retry_config dict if provided
    retry_config = None
    if request.retry_config:
        retry_config = request.retry_config.model_dump()

    # Build schedule_config dict if provided
    schedule_config = None
    if request.schedule_config:
        schedule_config = request.schedule_config.model_dump()

    # Build circuit_breaker dict if provided
    circuit_breaker_config = None
    if request.circuit_breaker:
        circuit_breaker_config = request.circuit_breaker.model_dump()

    campaign = await db_client.create_campaign(
        name=request.name,
        workflow_id=request.workflow_id,
        source_type=request.source_type,
        source_id=request.source_id,
        user_id=user.id,
        organization_id=user.selected_organization_id,
        retry_config=retry_config,
        max_concurrency=request.max_concurrency,
        schedule_config=schedule_config,
        circuit_breaker=circuit_breaker_config,
        telephony_configuration_id=telephony_configuration_id,
    )

    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign, workflow_name, telephony_configuration_name=cfg_name
    )


@router.get("/")
async def get_campaigns(
    user: UserModel = Depends(get_user),
) -> CampaignsResponse:
    """Get campaigns for user's organization"""
    campaigns = await db_client.get_campaigns(user.selected_organization_id)

    # Get workflow names for all campaigns
    workflow_ids = list(set(c.workflow_id for c in campaigns))
    workflows = await db_client.get_workflows_by_ids(
        workflow_ids, user.selected_organization_id
    )
    workflow_map = {w.id: w.name for w in workflows}

    stats_map = await db_client.get_queued_runs_stats_for_campaigns(
        [c.id for c in campaigns]
    )

    # Build {config_id: name} map by fetching all configs for the org once,
    # rather than one lookup per campaign.
    org_configs = await db_client.list_telephony_configurations(
        user.selected_organization_id
    )
    config_name_map = {cfg.id: cfg.name for cfg in org_configs}

    campaign_responses = [
        _build_campaign_response(
            c,
            workflow_map.get(c.workflow_id, "Unknown"),
            executed_count=stats_map.get(c.id, {}).get("executed", 0),
            total_queued_count=stats_map.get(c.id, {}).get("total", 0),
            telephony_configuration_name=config_name_map.get(
                c.telephony_configuration_id
            ),
        )
        for c in campaigns
    ]

# =====================================================================
# CLINIC-AGNOSTIC CLINIC DETAILS & APPOINTMENT SCHEDULING MANAGEMENT
# =====================================================================
from sqlalchemy import text
from api.services.prompt_compiler import (
    DEFAULT_CLINIC_SETTINGS,
    compile_unified_prompt,
)

CLINIC_SETTINGS_KEY = "clinic_settings"
BOOK_APPOINTMENT_TOOL_UUID = "c84e1234-5678-4321-9876-abcdef012345"


class BranchInfoPayload(BaseModel):
    id: str
    name: str
    address: str = ""
    landmark: str = ""
    phone: str = ""


class TimeChunkPayload(BaseModel):
    start: str
    end: str


class AppointmentConfigPayload(BaseModel):
    enabled: bool = False
    allow_booking: bool = True
    schedule: Dict[str, Dict[str, List[TimeChunkPayload]]] = Field(default_factory=dict)


class ClinicSettingsPayload(BaseModel):
    clinic_name: str
    doctor_name: str
    doctor_credentials: Optional[str] = ""
    official_reception: Optional[str] = ""
    email: Optional[str] = ""
    branches: List[BranchInfoPayload] = Field(default_factory=list)
    procedures: Optional[str] = ""
    special_notes: Optional[str] = ""
    appointment_config: AppointmentConfigPayload


class BookAppointmentPayload(BaseModel):
    patient_name: str
    phone_number: str
    branch_id: str
    appointment_date: str
    appointment_time: str
    procedure_of_interest: Optional[str] = ""
    booked_by: Optional[str] = "voice_agent"
    notes: Optional[str] = ""


class UpdateAppointmentStatusPayload(BaseModel):
    status: str
    notes: Optional[str] = None


class EditAppointmentPayload(BaseModel):
    patient_name: Optional[str] = None
    phone_number: Optional[str] = None
    branch_id: Optional[str] = None
    appointment_date: Optional[str] = None
    appointment_time: Optional[str] = None
    procedure_of_interest: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None



def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Parse time strings like '11:00 AM', '03:30 PM', '15:30', '11:00' to minutes from midnight."""
    if not time_str:
        return None
    clean = time_str.strip().upper().replace(".", "").strip()
    clean = " ".join(clean.split())
    for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(clean, fmt)
            return t.hour * 60 + t.minute
        except ValueError:
            continue
    return None


def is_time_in_chunks(time_minutes: int, chunks: List[Dict[str, str]]) -> bool:
    """Check if time_minutes falls within any [start, end] chunk."""
    for chunk in chunks:
        start_min = parse_time_to_minutes(chunk.get("start", ""))
        end_min = parse_time_to_minutes(chunk.get("end", ""))
        if start_min is not None and end_min is not None:
            if start_min <= time_minutes <= end_min:
                return True
    return False


async def _resolve_org_id(request: Request) -> int:
    """Extract organization_id from user auth header if available, else default to 1."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            from api.services.auth.jwt import decode_access_token
            token = auth_header.split(" ")[1]
            token_data = decode_access_token(token)
            if token_data and "sub" in token_data:
                user = await db_client.get_user_by_id(int(token_data["sub"]))
                if user and user.selected_organization_id:
                    return user.selected_organization_id
        except Exception:
            pass
    return 1


@router.get("/clinic-settings")
async def get_clinic_settings(
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """Retrieve the current organization's clinic details and appointment schedule."""
    org_id = user.selected_organization_id
    try:
        async with db_client.async_session() as session:
            res = await session.execute(
                text("SELECT value FROM organization_configurations WHERE organization_id = :org_id AND LOWER(key) = LOWER(:key);"),
                {"org_id": org_id, "key": CLINIC_SETTINGS_KEY},
            )
            row = res.first()
            if row and row[0]:
                val = row[0]
                if isinstance(val, str):
                    val = json.loads(val)
                return {"success": True, "settings": val}
    except Exception:
        pass
    return {"success": True, "settings": DEFAULT_CLINIC_SETTINGS}


@router.post("/clinic-settings")
async def update_clinic_settings(
    payload: ClinicSettingsPayload,
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """
    Save clinic details and appointment schedule, dynamically recompile
    the voice agent system prompt, and gate the book_appointment tool in workflow_definitions.
    """
    org_id = user.selected_organization_id
    settings_dict = payload.model_dump()
    is_timings_enabled = bool(settings_dict.get("appointment_config", {}).get("enabled", False))
    is_booking_enabled = is_timings_enabled and bool(settings_dict.get("appointment_config", {}).get("allow_booking", True))

    # 1. Persist to organization_configurations
    async with db_client.async_session() as session:
        await session.execute(
            text("""
                INSERT INTO organization_configurations (organization_id, key, value, created_at, updated_at)
                VALUES (:org_id, :key, :val, NOW(), NOW())
                ON CONFLICT (organization_id, key) DO UPDATE
                SET value = :val, updated_at = NOW();
            """),
            {"org_id": org_id, "key": CLINIC_SETTINGS_KEY, "val": json.dumps(settings_dict)},
        )
        await session.commit()

    # 2. Compile updated clinic-agnostic voice agent prompt
    new_prompt = compile_unified_prompt(settings_dict)

    # 3. Update published workflow definition in PostgreSQL (prompt + tool gating)
    async with db_client.async_session() as session:
        res = await session.execute(
            text("""
                SELECT wd.id, wd.workflow_json 
                FROM workflow_definitions wd
                JOIN workflows w ON wd.workflow_id = w.id
                WHERE (w.organization_id = :org_id OR :org_id IS NULL OR w.id = 1)
                  AND wd.status = 'published'
                ORDER BY wd.id DESC LIMIT 1;
            """),
            {"org_id": org_id},
        )
        row = res.first()
        if row:
            def_id = row.id
            wf_json = row.workflow_json
            if isinstance(wf_json, str):
                wf_json = json.loads(wf_json)

            nodes = wf_json.get("nodes", [])
            for node in nodes:
                node_data = node.get("data", {})
                if node.get("type") in ("startCall", "agentNode") or node_data.get("is_start"):
                    node["data"]["prompt"] = new_prompt
                    
                    # Tool schema gating: Level 1 master toggle
                    tools = list(node_data.get("tool_uuids") or [])
                    if is_booking_enabled:
                        if BOOK_APPOINTMENT_TOOL_UUID not in tools:
                            tools.append(BOOK_APPOINTMENT_TOOL_UUID)
                    else:
                        tools = [t for t in tools if t != BOOK_APPOINTMENT_TOOL_UUID]
                    node["data"]["tool_uuids"] = tools
                    break
            else:
                if nodes and "data" in nodes[0]:
                    nodes[0]["data"]["prompt"] = new_prompt
                    tools = list(nodes[0]["data"].get("tool_uuids") or [])
                    if is_booking_enabled:
                        if BOOK_APPOINTMENT_TOOL_UUID not in tools:
                            tools.append(BOOK_APPOINTMENT_TOOL_UUID)
                    else:
                        tools = [t for t in tools if t != BOOK_APPOINTMENT_TOOL_UUID]
                    nodes[0]["data"]["tool_uuids"] = tools

            await session.execute(
                text("""
                    UPDATE workflow_definitions
                    SET workflow_json = :data
                    WHERE id = :id;
                """),
                {"data": json.dumps(wf_json), "id": def_id},
            )
            await session.commit()

    return {
        "success": True,
        "message": "Clinic settings saved, voice agent prompt updated, and booking tools synced successfully",
        "settings": settings_dict,
    }


@router.get("/appointments")
async def get_appointments(
    appointment_date: Optional[str] = Query(None, description="YYYY-MM-DD date filter"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by patient name, phone, or procedure"),
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """Retrieve appointments with daily shift statistics and filtering for reception staff."""
    org_id = user.selected_organization_id or 1
    
    conditions = ["organization_id = :org_id"]
    params: Dict[str, Any] = {"org_id": org_id}
    
    if appointment_date:
        try:
            parsed_date = datetime.strptime(appointment_date.strip(), "%Y-%m-%d").date()
            conditions.append("appointment_date = :appointment_date")
            params["appointment_date"] = parsed_date
        except ValueError:
            pass
        
    if branch_id and branch_id != "all":
        conditions.append("branch_id = :branch_id")
        params["branch_id"] = branch_id
        
    if status and status != "all":
        conditions.append("status = :status")
        params["status"] = status
        
    if search:
        conditions.append("(patient_name ILIKE :search OR phone_number ILIKE :search OR procedure_of_interest ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
        
    where_clause = " AND ".join(conditions)
    
    async with db_client.async_session() as session:
        # 1. Fetch filtered appointments
        stmt = text(f"""
            SELECT id, organization_id, branch_id, branch_name, patient_name, phone_number,
                   procedure_of_interest, appointment_date, appointment_time, time_window,
                   booked_by, status, notes, whatsapp_sent, created_at, updated_at
            FROM appointments
            WHERE {where_clause}
            ORDER BY appointment_date ASC, appointment_time ASC;
        """)
        res = await session.execute(stmt, params)
        rows = res.fetchall()
        
        appointments = []
        for r in rows:
            appointments.append({
                "id": r.id,
                "organization_id": r.organization_id,
                "branch_id": r.branch_id,
                "branch_name": r.branch_name,
                "patient_name": r.patient_name,
                "phone_number": r.phone_number,
                "procedure_of_interest": r.procedure_of_interest or "",
                "appointment_date": str(r.appointment_date),
                "appointment_time": r.appointment_time,
                "time_window": r.time_window or "",
                "booked_by": r.booked_by,
                "status": r.status,
                "notes": r.notes or "",
                "whatsapp_sent": bool(r.whatsapp_sent),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })
            
        # 2. Shift Metrics
        metrics_conditions = ["organization_id = :org_id"]
        metrics_params: Dict[str, Any] = {"org_id": org_id}
        if appointment_date:
            try:
                parsed_date = datetime.strptime(appointment_date.strip(), "%Y-%m-%d").date()
                metrics_conditions.append("appointment_date = :appointment_date")
                metrics_params["appointment_date"] = parsed_date
            except ValueError:
                pass
        if branch_id and branch_id != "all":
            metrics_conditions.append("branch_id = :branch_id")
            metrics_params["branch_id"] = branch_id
            
        metrics_where = " AND ".join(metrics_conditions)
        metrics_res = await session.execute(
            text(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'confirmed') as confirmed,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
                    COUNT(*) FILTER (WHERE status = 'no_show') as no_show
                FROM appointments
                WHERE {metrics_where};
            """),
            metrics_params,
        )
        metrics_row = metrics_res.first()
        shift_metrics = {
            "total": int(metrics_row.total) if metrics_row else 0,
            "confirmed": int(metrics_row.confirmed) if metrics_row else 0,
            "completed": int(metrics_row.completed) if metrics_row else 0,
            "cancelled": int(metrics_row.cancelled) if metrics_row else 0,
            "no_show": int(metrics_row.no_show) if metrics_row else 0,
        }
        
    return {
        "success": True,
        "appointments": appointments,
        "shift_metrics": shift_metrics,
        "count": len(appointments),
    }


@router.post("/appointments/book")
async def book_appointment(
    payload: BookAppointmentPayload,
    request: Request,
) -> Dict[str, Any]:
    """
    Dual-access endpoint for booking patient consultations (Staff Dashboard & Voice AI Agent).
    Enforces strict two-level validation against clinic hours and weekly chunk sessions.
    """
    org_id = await _resolve_org_id(request)
    
    # 1. Fetch clinic configuration
    settings_dict = DEFAULT_CLINIC_SETTINGS
    try:
        async with db_client.async_session() as session:
            res = await session.execute(
                text("SELECT value FROM organization_configurations WHERE organization_id = :org_id AND key = :key;"),
                {"org_id": org_id, "key": CLINIC_SETTINGS_KEY},
            )
            row = res.first()
            if row and row[0]:
                val = row[0]
                if isinstance(val, str):
                    val = json.loads(val)
                settings_dict = val
    except Exception:
        pass
        
    appt_cfg = settings_dict.get("appointment_config", {})
    
    # Level 1 Gate: Master Toggles (applies to Voice AI Agent)
    is_staff = (payload.booked_by == "staff") or bool(request.headers.get("authorization"))
    if not is_staff:
        if not appt_cfg.get("enabled", False):
            return {
                "success": False,
                "error": "Appointment scheduling is currently paused at the clinic. Please connect with our reception desk.",
            }
        if not appt_cfg.get("allow_booking", True):
            reception = settings_dict.get("official_reception", "our clinic reception")
            return {
                "success": False,
                "error": f"Direct appointment booking is handled by our reception desk. Please contact reception at {reception} to schedule.",
            }
        
    # Level 2 Gate: Branch verification
    branches = settings_dict.get("branches", [])
    branch_map = {b.get("id", "").lower(): b for b in branches}
    req_branch_id = payload.branch_id.strip().lower()
    
    matched_branch = branch_map.get(req_branch_id)
    if not matched_branch:
        for b in branches:
            if req_branch_id in b.get("id", "").lower() or req_branch_id in b.get("name", "").lower():
                matched_branch = b
                req_branch_id = b.get("id", "").lower()
                break
                
    if not matched_branch:
        valid_names = ", ".join([b.get("name", b.get("id", "")) for b in branches])
        return {
            "success": False,
            "error": f"Branch '{payload.branch_id}' was not recognized. Available branches: {valid_names}.",
        }
        
    branch_name = matched_branch.get("name", req_branch_id.capitalize())
    
    # Date validation
    try:
        target_date = datetime.strptime(payload.appointment_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        return {
            "success": False,
            "error": f"Invalid appointment date format '{payload.appointment_date}'. Please provide date in YYYY-MM-DD format.",
        }
        
    day_name = target_date.strftime("%A").lower()
    
    # Schedule check
    schedule = appt_cfg.get("schedule", {})
    branch_schedule = schedule.get(req_branch_id, {})
    day_chunks = branch_schedule.get(day_name, [])
    
    if not day_chunks:
        return {
            "success": False,
            "error": f"{branch_name} is closed on {day_name.capitalize()}s. Please choose another day or branch.",
        }
        
    # Time chunk check
    req_time_min = parse_time_to_minutes(payload.appointment_time)
    if req_time_min is None:
        return {
            "success": False,
            "error": f"Invalid appointment time format '{payload.appointment_time}'. Please provide a valid time such as '11:30 AM' or '04:00 PM'.",
        }
        
    if not is_time_in_chunks(req_time_min, day_chunks):
        chunk_strs = [f"{c.get('start')} to {c.get('end')}" for c in day_chunks if c.get('start') and c.get('end')]
        avail_text = ", ".join(chunk_strs) if chunk_strs else "Closed"
        return {
            "success": False,
            "error": f"The requested time {payload.appointment_time} is outside operating hours for {branch_name} on {day_name.capitalize()}. Available session timings are: {avail_text}. Please choose a time within these slots.",
        }
        
    # Insert confirmed appointment record
    async with db_client.async_session() as session:
        insert_stmt = text("""
            INSERT INTO appointments (
                organization_id, branch_id, branch_name, patient_name, phone_number,
                procedure_of_interest, appointment_date, appointment_time,
                booked_by, status, notes, whatsapp_sent, created_at, updated_at
            ) VALUES (
                :org_id, :branch_id, :branch_name, :patient_name, :phone_number,
                :procedure_of_interest, :appointment_date, :appointment_time,
                :booked_by, 'confirmed', :notes, FALSE, NOW(), NOW()
            ) RETURNING id;
        """)
        res = await session.execute(
            insert_stmt,
            {
                "org_id": org_id,
                "branch_id": req_branch_id,
                "branch_name": branch_name,
                "patient_name": payload.patient_name.strip(),
                "phone_number": payload.phone_number.strip(),
                "procedure_of_interest": (payload.procedure_of_interest or "").strip(),
                "appointment_date": target_date,
                "appointment_time": payload.appointment_time.strip(),
                "booked_by": payload.booked_by or "voice_agent",
                "notes": (payload.notes or "").strip(),
            },
        )
        new_row = res.first()
        appointment_id = new_row[0] if new_row else None
        await session.commit()

    # Automatically dispatch WhatsApp appointment confirmation in background
    if appointment_id and payload.phone_number:
        async def _dispatch_whatsapp_async(appt_id: int, p_num: str, p_name: str, a_dt: str, b_name: str, proc: str):
            endpoints = [
                "http://dograhtest-analysis:8001/send-whatsapp",
                "http://127.0.0.1:8001/send-whatsapp",
            ]
            whatsapp_body = {
                "template_type": "appointment_confirmation",
                "phone_number": p_num,
                "caller_name": p_name,
                "appointment_datetime": a_dt,
                "branch": b_name,
                "procedure_of_interest": proc,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    for ep in endpoints:
                        try:
                            resp = await client.post(ep, json=whatsapp_body)
                            if resp.status_code in (200, 201):
                                res_json = resp.json()
                                if res_json.get("success"):
                                    logger.info(f"WhatsApp confirmation dispatched for appointment {appt_id} to {p_num}")
                                    async with db_client.async_session() as s:
                                        await s.execute(
                                            text("UPDATE appointments SET whatsapp_sent = TRUE, updated_at = NOW() WHERE id = :id;"),
                                            {"id": appt_id}
                                        )
                                        await s.commit()
                                    break
                        except Exception as ep_err:
                            logger.debug(f"WhatsApp dispatch attempt failed on {ep}: {ep_err}")
            except Exception as exc:
                logger.error(f"Error in async WhatsApp dispatch for appointment {appt_id}: {exc}")

        formatted_datetime = f"{target_date.strftime('%A, %d %B %Y')} at {payload.appointment_time.strip()}"
        asyncio.create_task(_dispatch_whatsapp_async(
            appointment_id,
            payload.phone_number.strip(),
            payload.patient_name.strip(),
            formatted_datetime,
            branch_name,
            (payload.procedure_of_interest or "").strip()
        ))
        
    return {
        "success": True,
        "booking_id": appointment_id,
        "message": f"Appointment successfully confirmed for {payload.patient_name} on {payload.appointment_date} at {payload.appointment_time} at {branch_name}.",
        "appointment": {
            "id": appointment_id,
            "patient_name": payload.patient_name,
            "phone_number": payload.phone_number,
            "branch_id": req_branch_id,
            "branch_name": branch_name,
            "appointment_date": str(target_date),
            "appointment_time": payload.appointment_time,
            "procedure_of_interest": payload.procedure_of_interest,
            "booked_by": payload.booked_by or "voice_agent",
            "status": "confirmed",
        },
    }


@router.patch("/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    payload: UpdateAppointmentStatusPayload,
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """Update appointment status (confirmed, completed, cancelled, no_show) and notes."""
    org_id = user.selected_organization_id or 1
    valid_statuses = ("confirmed", "completed", "cancelled", "no_show")
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'. Valid statuses: {valid_statuses}")
        
    async with db_client.async_session() as session:
        if payload.notes is not None:
            stmt = text("""
                UPDATE appointments
                SET status = :status, notes = :notes, updated_at = NOW()
                WHERE id = :id AND organization_id = :org_id
                RETURNING id;
            """)
            params = {"status": payload.status, "notes": payload.notes, "id": appointment_id, "org_id": org_id}
        else:
            stmt = text("""
                UPDATE appointments
                SET status = :status, updated_at = NOW()
                WHERE id = :id AND organization_id = :org_id
                RETURNING id;
            """)
            params = {"status": payload.status, "id": appointment_id, "org_id": org_id}
            
        res = await session.execute(stmt, params)
        if not res.first():
            raise HTTPException(status_code=404, detail="Appointment not found")
        await session.commit()
        
    return {"success": True, "message": f"Appointment #{appointment_id} status updated to {payload.status}"}


@router.patch("/appointments/{appointment_id}")
async def edit_appointment(
    appointment_id: int,
    payload: EditAppointmentPayload,
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """Edit appointment details, status, or notes."""
    org_id = user.selected_organization_id or 1
    
    async with db_client.async_session() as session:
        res = await session.execute(
            text("SELECT id, branch_id, appointment_date, appointment_time FROM appointments WHERE id = :id AND organization_id = :org_id;"),
            {"id": appointment_id, "org_id": org_id},
        )
        existing = res.first()
        if not existing:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        update_fields = {}
        if payload.patient_name is not None and payload.patient_name.strip():
            update_fields["patient_name"] = payload.patient_name.strip()
            
        if payload.phone_number is not None and payload.phone_number.strip():
            update_fields["phone_number"] = payload.phone_number.strip()
            
        if payload.procedure_of_interest is not None:
            update_fields["procedure_of_interest"] = payload.procedure_of_interest.strip()
            
        if payload.notes is not None:
            update_fields["notes"] = payload.notes.strip()
            
        if payload.status is not None:
            valid_statuses = ("confirmed", "completed", "cancelled", "no_show")
            if payload.status not in valid_statuses:
                raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'")
            update_fields["status"] = payload.status
            
        if payload.branch_id is not None and payload.branch_id.strip():
            target_branch_id = payload.branch_id.strip().lower()
            update_fields["branch_id"] = target_branch_id
            try:
                cfg_res = await session.execute(
                    text("SELECT value FROM organization_configurations WHERE organization_id = :org_id AND key = :key;"),
                    {"org_id": org_id, "key": CLINIC_SETTINGS_KEY},
                )
                cfg_row = cfg_res.first()
                if cfg_row and cfg_row[0]:
                    s = cfg_row[0]
                    if isinstance(s, str):
                        s = json.loads(s)
                    for b in s.get("branches", []):
                        if b.get("id", "").lower() == target_branch_id:
                            update_fields["branch_name"] = b.get("name", target_branch_id.capitalize())
                            break
            except Exception:
                pass
                
        if payload.appointment_date is not None and payload.appointment_date.strip():
            try:
                parsed_d = datetime.strptime(payload.appointment_date.strip(), "%Y-%m-%d").date()
                update_fields["appointment_date"] = parsed_d
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
                
        if payload.appointment_time is not None and payload.appointment_time.strip():
            update_fields["appointment_time"] = payload.appointment_time.strip()
            
        if not update_fields:
            return {"success": True, "message": "No changes were made."}
            
        set_clauses = [f"{k} = :{k}" for k in update_fields.keys()]
        set_clauses.append("updated_at = NOW()")
        params = {**update_fields, "id": appointment_id, "org_id": org_id}
        
        await session.execute(
            text(f"UPDATE appointments SET {', '.join(set_clauses)} WHERE id = :id AND organization_id = :org_id;"),
            params,
        )
        await session.commit()
        
    return {"success": True, "message": f"Appointment #{appointment_id} updated successfully"}


@router.delete("/appointments/{appointment_id}")
async def delete_appointment(
    appointment_id: int,
    user: UserModel = Depends(get_user),
) -> Dict[str, Any]:
    """Delete an appointment record."""
    org_id = user.selected_organization_id or 1
    async with db_client.async_session() as session:
        res = await session.execute(
            text("DELETE FROM appointments WHERE id = :id AND organization_id = :org_id RETURNING id;"),
            {"id": appointment_id, "org_id": org_id},
        )
        if not res.first():
            raise HTTPException(status_code=404, detail="Appointment not found")
        await session.commit()
    return {"success": True, "message": f"Appointment #{appointment_id} deleted successfully"}


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Get campaign details"""
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    workflow_name = await db_client.get_workflow_name(
        campaign.workflow_id, organization_id=user.selected_organization_id
    )

    executed, total = await _get_campaign_stats(campaign.id)
    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Start campaign execution"""
    # Block start if the org has no telephony configuration at all.
    configs = await db_client.list_telephony_configurations(
        user.selected_organization_id
    )
    if not configs:
        raise HTTPException(
            status_code=401,
            detail="You must configure telephony first by going to APP_URL/configure-telephony",
        )

    # Verify campaign exists and belongs to organization
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check Dograh quota before starting campaign (apply per-workflow
    # model_overrides so we evaluate the keys this campaign will use).
    quota_result = await authorize_workflow_run_start(
        workflow_id=campaign.workflow_id,
        organization_id=user.selected_organization_id,
        actor_user=user,
    )
    if not quota_result.has_quota:
        raise HTTPException(status_code=402, detail=quota_result.error_message)

    # Start the campaign using the runner service
    try:
        await campaign_runner_service.start_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get updated campaign
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    workflow_name = await db_client.get_workflow_name(
        campaign.workflow_id, organization_id=user.selected_organization_id
    )

    executed, total = await _get_campaign_stats(campaign.id)
    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Pause campaign execution"""
    # Verify campaign exists and belongs to organization
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Pause the campaign using the runner service
    try:
        await campaign_runner_service.pause_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get updated campaign
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    workflow_name = await db_client.get_workflow_name(
        campaign.workflow_id, organization_id=user.selected_organization_id
    )

    executed, total = await _get_campaign_stats(campaign.id)
    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    request: UpdateCampaignRequest,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Update campaign settings (name, retry config, max concurrency, schedule)"""
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.state in ["completed", "failed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update a {campaign.state} campaign",
        )

    if request.max_concurrency is not None:
        await _validate_max_concurrency(
            request.max_concurrency, user.selected_organization_id
        )

    # Build update kwargs
    update_kwargs = {}

    if request.name is not None:
        update_kwargs["name"] = request.name

    if request.retry_config is not None:
        update_kwargs["retry_config"] = request.retry_config.model_dump()

    # Merge max_concurrency and schedule_config into orchestrator_metadata
    metadata = campaign.orchestrator_metadata or {}
    metadata_changed = False

    if request.max_concurrency is not None:
        metadata["max_concurrency"] = request.max_concurrency
        metadata_changed = True

    if request.schedule_config is not None:
        metadata["schedule_config"] = request.schedule_config.model_dump()
        metadata_changed = True

    if request.circuit_breaker is not None:
        metadata["circuit_breaker"] = request.circuit_breaker.model_dump()
        metadata_changed = True

    if metadata_changed:
        update_kwargs["orchestrator_metadata"] = metadata

    if update_kwargs:
        await db_client.update_campaign(campaign_id=campaign_id, **update_kwargs)

    # Re-fetch to return updated data
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    workflow_name = await db_client.get_workflow_name(
        campaign.workflow_id, organization_id=user.selected_organization_id
    )

    executed, total = await _get_campaign_stats(campaign.id)
    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.get("/{campaign_id}/runs")
async def get_campaign_runs(
    campaign_id: int,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(50, ge=1, le=100, description="Number of items per page"),
    filters: Optional[str] = Query(None, description="JSON-encoded filter criteria"),
    sort_by: Optional[str] = Query(
        None, description="Field to sort by (e.g., 'duration', 'created_at')"
    ),
    sort_order: Optional[str] = Query(
        "desc", description="Sort order ('asc' or 'desc')"
    ),
    user: UserModel = Depends(get_user),
) -> CampaignRunsResponse:
    """Get campaign workflow runs with pagination, filters and sorting"""
    offset = (page - 1) * limit

    # Parse filters if provided
    filter_criteria = []
    if filters:
        try:
            filter_criteria = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filter format")

        # Restrict allowed filter attributes for regular users
        allowed_attributes = {
            "dateRange",
            "dispositionCode",
            "duration",
            "status",
            "tokenUsage",
        }
        for filter_item in filter_criteria:
            attribute = filter_item.get("attribute")
            if attribute and attribute not in allowed_attributes:
                raise HTTPException(
                    status_code=403, detail=f"Invalid attribute '{attribute}'"
                )

    try:
        runs, total_count = await db_client.get_campaign_runs_paginated(
            campaign_id,
            user.selected_organization_id,
            limit=limit,
            offset=offset,
            filters=filter_criteria if filter_criteria else None,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    total_pages = (total_count + limit - 1) // limit

    return CampaignRunsResponse(
        runs=[run.model_dump() for run in runs],
        total_count=total_count,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


class RedialCampaignRequest(BaseModel):
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Name for the redial campaign"
    )
    retry_on_voicemail: bool = True
    retry_on_no_answer: bool = True
    retry_on_busy: bool = True
    retry_config: Optional[RetryConfigRequest] = None

    @model_validator(mode="after")
    def validate_at_least_one_reason(self):
        if not (
            self.retry_on_voicemail or self.retry_on_no_answer or self.retry_on_busy
        ):
            raise ValueError(
                "At least one of retry_on_voicemail, retry_on_no_answer, "
                "retry_on_busy must be true"
            )
        return self


@router.post("/{campaign_id}/redial")
async def redial_campaign(
    campaign_id: int,
    request: RedialCampaignRequest,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Create a new campaign that re-dials unique subscribers from a completed
    campaign whose latest call resulted in voicemail, no-answer, or busy.

    The new campaign is created in 'created' state with queued_runs pre-seeded
    from the parent's original initial contexts. A campaign can be redialed at
    most once.
    """
    parent = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if parent.state != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Only completed campaigns can be redialed (current state: {parent.state})",
        )

    parent_meta = parent.orchestrator_metadata or {}
    if parent_meta.get("redialed_campaign_id"):
        raise HTTPException(
            status_code=400,
            detail="This campaign has already been redialed",
        )

    candidates = await db_client.get_redial_candidates(
        campaign_id=parent.id,
        include_voicemail=request.retry_on_voicemail,
        include_no_answer=request.retry_on_no_answer,
        include_busy=request.retry_on_busy,
    )
    if not candidates:
        raise HTTPException(
            status_code=400,
            detail="No subscribers match the selected redial criteria",
        )

    queued_runs_data = [
        {
            "campaign_id": 0,  # replaced inside create_redial_campaign
            "source_uuid": c["source_uuid"],
            "context_variables": c["context_variables"],
            "state": "queued",
        }
        for c in candidates
    ]

    retry_config = (
        request.retry_config.model_dump()
        if request.retry_config
        else parent.retry_config
    )
    new_name = request.name or f"{parent.name} (Redial)"

    try:
        child = await db_client.create_redial_campaign(
            parent_campaign=parent,
            new_name=new_name,
            retry_config=retry_config,
            queued_runs_data=queued_runs_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    workflow_name = await db_client.get_workflow_name(
        child.workflow_id, organization_id=user.selected_organization_id
    )
    executed, total = await _get_campaign_stats(child.id)
    cfg_name = await _get_telephony_configuration_name(
        child.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        child,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignResponse:
    """Resume a paused campaign"""
    # Block resume if the org has no telephony configuration at all.
    configs = await db_client.list_telephony_configurations(
        user.selected_organization_id
    )
    if not configs:
        raise HTTPException(
            status_code=401,
            detail="You must configure telephony first by going to APP_URL/configure-telephony",
        )

    # Verify campaign exists and belongs to organization
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check Dograh quota before resuming campaign (apply per-workflow
    # model_overrides so we evaluate the keys this campaign will use).
    quota_result = await authorize_workflow_run_start(
        workflow_id=campaign.workflow_id,
        organization_id=user.selected_organization_id,
        actor_user=user,
    )
    if not quota_result.has_quota:
        raise HTTPException(status_code=402, detail=quota_result.error_message)

    # Resume the campaign using the runner service
    try:
        await campaign_runner_service.resume_campaign(campaign_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get updated campaign
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    workflow_name = await db_client.get_workflow_name(
        campaign.workflow_id, organization_id=user.selected_organization_id
    )

    executed, total = await _get_campaign_stats(campaign.id)
    cfg_name = await _get_telephony_configuration_name(
        campaign.telephony_configuration_id, user.selected_organization_id
    )
    return _build_campaign_response(
        campaign,
        workflow_name or "Unknown",
        executed,
        total,
        telephony_configuration_name=cfg_name,
    )


@router.get("/{campaign_id}/progress")
async def get_campaign_progress(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignProgressResponse:
    """Get current campaign progress and statistics"""
    # Verify campaign exists and belongs to organization
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get progress from runner service
    try:
        progress = await campaign_runner_service.get_campaign_status(campaign_id)
        return CampaignProgressResponse(**progress)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CampaignSourceDownloadResponse(BaseModel):
    download_url: str
    expires_in: int


@router.get("/{campaign_id}/source-download-url")
async def get_campaign_source_download_url(
    campaign_id: int,
    user: UserModel = Depends(get_user),
) -> CampaignSourceDownloadResponse:
    """Get presigned download URL for campaign CSV source file
    Validates that the campaign belongs to the user's organization for security.
    """
    # Verify campaign exists and belongs to organization
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Only generate download URL for CSV files
    if campaign.source_type != "csv":
        raise HTTPException(
            status_code=400,
            detail=f"Download URL only available for CSV sources. This campaign uses {campaign.source_type}",
        )

    # Verify the file key belongs to the user's organization
    # File key format: campaigns/{org_id}/{uuid}_{filename}.csv
    if not campaign.source_id.startswith(f"campaigns/{user.selected_organization_id}/"):
        raise HTTPException(
            status_code=403,
            detail="Access denied: Source file does not belong to your organization",
        )

    # Generate presigned download URL
    try:
        download_url = await storage_fs.aget_signed_url(
            campaign.source_id,
            expiration=3600,  # 1 hour
        )

        if not download_url:
            raise HTTPException(
                status_code=500, detail="Failed to generate download URL"
            )

        return CampaignSourceDownloadResponse(
            download_url=download_url, expires_in=3600
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/{campaign_id}/report")
async def download_campaign_report(
    campaign_id: int,
    user: UserModel = Depends(get_user),
    start_date: Optional[datetime] = Query(
        None, description="Filter runs created on or after this datetime (ISO 8601)"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter runs created on or before this datetime (ISO 8601)"
    ),
) -> StreamingResponse:
    """Download a CSV report of completed campaign runs."""
    campaign = await db_client.get_campaign(campaign_id, user.selected_organization_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    output, filename = await generate_campaign_report_csv(
        campaign_id, start_date=start_date, end_date=end_date
    )

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


