import json, os, sys
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("src"))
from sca2_workbench import export as EX

old_root = os.environ["TMPDIR"] + "/exports_old"
sess = EX.Session()
cases = [("smol_base", "bank_USA_00023ac74dac"),
         ("smol_inst", "wvs_Q57"),
         ("smol_inst_usa_e1", "bank_USA_00023ac74dac")]
for key, item_id in cases:
    item = EX.item_from_id(item_id)
    man, b, out = EX.capture_run(sess, key, item)
    stored = json.load(open("exports/run__%s__%s.json" % (key, item_id)))
    print("%-18s %-24s recomputed margin=%.15f stored=%.15f  diff=%.2e  margin_c=%.12f vs %.12f  eq6=%.2e" % (
        key, item_id, man["readout"]["margin"], stored["readout"]["margin"],
        abs(man["readout"]["margin"] - stored["readout"]["margin"]),
        man["readout"]["margin_clamped"], stored["readout"]["margin_clamped"],
        man["conservation"]["eq6_teacher_forced_max_abs_gap"]))
    print("      conservation pass:", man["conservation"]["pass"],
          "resid=%.2e dla=%.2e hf64=%.2e" % (man["conservation"]["residual_closure_inf"],
                                             man["conservation"]["dla_gap"],
                                             man["conservation"]["hf64_logits_max_rel_gap"]))
    if os.path.exists(old_root + "/run__%s__%s.json" % (key, item_id)):
        om = json.load(open(old_root + "/run__%s__%s.json" % (key, item_id)))
        print("      old(@1) margin=%.15f  diff=%.2e" % (om["readout"]["margin"], abs(om["readout"]["margin"] - man["readout"]["margin"])))
