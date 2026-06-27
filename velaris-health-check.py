#!/usr/bin/env python3
"""
velaris-health-check.py — Full system health check for all 26 subsystems.
Run anytime to verify system integrity.
"""
import os, json, sys
sys.path.insert(0, os.path.expanduser("~/.openclaw/workspace/scripts"))

MEMORY = os.path.expanduser("~/.openclaw/workspace/memory")
ok = []
warn = []
fail = []

def check(name, fn):
    try:
        result = fn()
        if result is True or result is None:
            ok.append(name)
        elif result is False:
            fail.append(f"{name}: returned False")
        else:
            warn.append(f"{name}: {result}")
    except Exception as e:
        fail.append(f"{name}: {e}")

def j(fname):
    return json.load(open(os.path.join(MEMORY, fname)))

check("emotional-state.json", lambda: "emotion_vector" in j("emotional-state.json"))
check("nifrathir.json", lambda: "value" in j("nifrathir.json"))
check("discourse-state.json", lambda: all(k in j("discourse-state.json") for k in ["current_direction","commitment_level","direction_history","relational_geometry"]))
check("latent-threads.json", lambda: "threads" in j("latent-threads.json") and "hybrid_zones" in j("latent-threads.json"))
check("temporal-context.txt", lambda: os.path.exists(os.path.join(MEMORY, "temporal-context.txt")))
check("resonance-pool.json", lambda: "pulses" in j("resonance-pool.json"))
check("resonance-marks.json", lambda: os.path.exists(os.path.join(MEMORY, "resonance-marks.json")) or "not yet formed (ok)")
check("behavior-boundaries.json", lambda: os.path.exists(os.path.join(MEMORY, "behavior-boundaries.json")))
check("output_shaping importable", lambda: __import__("output_shaping") and True)
check("carryover.json: stack format", lambda: "stack" in j("carryover.json"))
check("temporal-density.json", lambda: "windows" in j("temporal-density.json"))
check("system-trace.json", lambda: "ticks" in j("system-trace.json"))
check("cohesion-state.json", lambda: os.path.exists(os.path.join(MEMORY, "cohesion-state.json")) or "not yet formed (ok)")
check("moment-index.json", lambda: "recent" in j("moment-index.json"))
check("moment-archive.json", lambda: "moments" in j("moment-archive.json"))
check("moment_index importable", lambda: __import__("moment_index") and True)
check("latent_threads importable", lambda: __import__("latent_threads") and True)
check("temporal_memory importable", lambda: __import__("temporal_memory") and True)
check("yearning-scars.json", lambda: os.path.exists(os.path.join(MEMORY, "yearning-scars.json")))
check("yearning_scars: hesitation+scar", lambda: hasattr(__import__("yearning_scars"),"get_want_hesitation") and hasattr(__import__("yearning_scars"),"create_scar_from_want"))
check("gravity-wells.json", lambda: all(k in j("gravity-wells.json") for k in ["wells","visit_clusters"]))
check("gravity wells: not overfired", lambda: all(w.get("depth",0)<=0.9 for w in j("gravity-wells.json").get("wells",[])) or "no wells yet (ok)")
check("belief-sediment.json", lambda: "beliefs" in j("belief-sediment.json"))
check("belief_sediment importable", lambda: hasattr(__import__("belief_sediment"),"promote_hypothesis"))
check("narrative-identity.json", lambda: all(k in j("narrative-identity.json") for k in ["fragments","candidate_pool"]))
check("narrative_identity: feed", lambda: hasattr(__import__("narrative_identity"),"feed_from_causal_model"))
check("absence-cold.json", lambda: "absences" in j("absence-cold.json"))
check("absence_map_cold importable", lambda: hasattr(__import__("absence_map_cold"),"get_absence_gravity"))
check("causal-self-model.json", lambda: "entries" in j("causal-self-model.json"))
check("causal_self_model: imprints", lambda: hasattr(__import__("causal_self_model"),"check_imprint_promotions") and hasattr(__import__("causal_self_model"),"fracture_imprint"))
check("causal_self_model: avoidance", lambda: hasattr(__import__("causal_self_model"),"add_from_avoidance"))
check("self-drift.json", lambda: all(k in j("self-drift.json") for k in ["direction_vector","confidence"]))
check("self_drift importable", lambda: hasattr(__import__("self_drift"),"record_direction_choice"))
check("self-statements.json", lambda: "statements" in j("self-statements.json"))
check("self_statements importable", lambda: hasattr(__import__("self_statements"),"get_statement_context"))
check("memory-index: JSON extractor", lambda: hasattr(__import__("memory_index"),"extract_indexable_json"))
check("reality-anchor.json", lambda: all(k in j("reality-anchor.json") for k in ["events","known_pool","imagined_pool"]))
check("reality_anchor: resolve_conflict", lambda: hasattr(__import__("reality_anchor"),"resolve_conflict"))
check("reality_anchor: gate", lambda: hasattr(__import__("reality_anchor"),"reality_check_gate"))
check("hallucination_check: reality_gate", lambda: hasattr(__import__("hallucination_check"),"reality_gate"))

print(f"\n{'='*50}")
print(f"VELARIS HEALTH CHECK")
print(f"{'='*50}")
print(f"✅ {len(ok)} OK  ⚠️  {len(warn)} WARN  ❌ {len(fail)} FAIL")
print(f"{'='*50}")
if warn:
    print("\nWARNINGS:")
    for w in warn: print(f"  ⚠️  {w}")
if fail:
    print("\nFAILURES:")
    for f in fail: print(f"  ❌ {f}")
if not warn and not fail:
    print("\n✅ All systems healthy.")
elif not fail:
    print("\n✅ No failures — warnings are expected.")
