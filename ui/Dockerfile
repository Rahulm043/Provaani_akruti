# Patched Dograh UI for self-hosted OSS over plain HTTP.
#
# The upstream image hardcodes `secure:true` on the dograh_auth_token /
# dograh_auth_user session cookies. Browsers refuse to store Secure cookies
# on http:// origins, so login POST succeeds but the session cookie is dropped
# and the middleware bounces the user straight back to /auth/login with no
# error. This layer flips those cookies to non-Secure so login works.
FROM dograhai/dograh-ui:latest

RUN sed -i 's/{httpOnly:!0,secure:!0/{httpOnly:!0,secure:!1/g' \
    /app/.next/server/app/api/auth/session/route.js \
    /app/.next/server/app/api/auth/logout/route.js
