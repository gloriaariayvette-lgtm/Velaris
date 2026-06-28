#!/usr/bin/env bash
# self-model-update.sh — Weekly self-model and causality update.
SCRIPTS="${HOME}/.vintos/workspace/scripts"
export PYTHONPATH="${SCRIPTS}:${PYTHONPATH}"
python3 -c "
import sys; sys.path.insert(0, '${SCRIPTS}')
from causality_engine import run_weekly
run_weekly()
from causal_self_model import update_from_evidence
update_from_evidence()
from causal_observations import promote_to_hypotheses
promote_to_hypotheses()
from causal_cluster import get_strongest_cluster_summary
clusters = get_strongest_cluster_summary(3)
print(f'[self-model] {len(clusters)} clusters identified')
" >> "${HOME}/.vintos/logs/self-model.log" 2>&1
