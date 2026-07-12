# Verilator RTL signoff gate — all unit tests + chip top must pass

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/sim/verilator"

echo "=== RTL signoff gate ==="
make pe systolic tmr triplex top
echo "=== RTL signoff PASSED ==="
