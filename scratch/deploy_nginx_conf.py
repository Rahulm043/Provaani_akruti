import subprocess
import base64

with open(r"c:\Users\rahul\Desktop\Provaani_akruti\custom-ui\nginx-spa.conf", "rb") as f:
    conf_bytes = f.read()

b64 = base64.b64encode(conf_bytes).decode("ascii")

remote_script = f"""
echo "{b64}" | base64 -d > /home/rahul/Provaani_akruti/custom-ui/nginx-spa.conf
sudo docker cp /home/rahul/Provaani_akruti/custom-ui/nginx-spa.conf dograhtest-custom-ui:/etc/nginx/conf.d/default.conf
sudo docker exec dograhtest-custom-ui nginx -t
sudo docker exec dograhtest-custom-ui nginx -s reload
"""

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    remote_script
]

proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("stdout:\n", proc.stdout)
print("stderr:\n", proc.stderr)
