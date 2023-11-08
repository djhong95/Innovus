create_rc_corner -name typ.cap -cap_table {/icas/kits/tsmc180/sc/tcb018gbwp7t_270a/Back_End/lef/tcb018gbwp7t_270a/techfiles/captable/t018lo_1p6m_typical.captable} -preRoute_res {1.0} -preRoute_cap {1.0} -preRoute_clkres {0.0} -preRoute_clkcap {0.0} -postRoute_res {1.0} -postRoute_cap {1.0} -postRoute_xcap {1.0} -postRoute_clkres {0.0} -postRoute_clkcap {0.0}
create_library_set -name tcb018gbwp7tbc -timing {/icas/kits/tsmc180/sc/tcb018gbwp7t_270a/Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/tcb018gbwp7tbc.lib}
create_library_set -name tcb018gbwp7twc -timing {/icas/kits/tsmc180/sc/tcb018gbwp7t_270a/Front_End/timing_power_noise/NLDM/tcb018gbwp7t_270a/tcb018gbwp7twc.lib}
create_constraint_mode -name gln_sdc -sdc_files {../synth/result/.gln.sdc}
create_delay_corner -name bc -library_set {tcb018gbwp7tbc} -rc_corner {typ.cap}
create_delay_corner -name wc -library_set {tcb018gbwp7twc} -rc_corner {typ.cap}
create_analysis_view -name best_case -constraint_mode {gln_sdc} -delay_corner {bc}
create_analysis_view -name worst_case -constraint_mode {gln_sdc} -delay_corner {wc}
set_analysis_view -setup {worst_case} -hold {best_case}
