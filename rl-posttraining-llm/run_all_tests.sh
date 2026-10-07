#!/usr/bin/env bash
# Run every phase's tests plus the core smoke tests.
#
#   ./run_all_tests.sh
#
# Unimplemented functions report as TODO, not failure, so this doubles as a
# progress dashboard: run it any time to see how far through the course you are.
# Exit code is 0 unless something is actually broken (FAIL or ERROR).

set -uo pipefail
cd "$(dirname "$0")"

status=0

echo "############ core (common/) ############"
python3 common/test_common.py || status=1

for phase in phase0_foundations phase1_execution_reward phase2_phased_rewards \
             phase3_process_reward phase4_execution_free phase5_multiturn_schema \
             phase6_agentic_analysis phase7_capstone; do
    test_file=$(ls "$phase"/test_phase*.py 2>/dev/null | head -1)
    [ -z "$test_file" ] && continue
    echo
    echo "############ $phase ############"
    ( cd "$phase" && python3 "$(basename "$test_file")" ) || status=1
done

echo
if [ "$status" -eq 0 ]; then
    echo "Nothing broken. Remaining TODOs are your next exercises."
else
    echo "Some checks FAILED or ERRORED — see above."
fi
exit "$status"
