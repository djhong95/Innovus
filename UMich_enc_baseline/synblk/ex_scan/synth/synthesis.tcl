#===============================================#
#		READ LIBRARY							#
#===============================================#
source -echo -verbose ./DATA/library.tcl

#===============================================#
#		READ DESIGN								#
#===============================================#
source -echo -verbose ./DATA/read.tcl

#===============================================#
#		SET CONSTRAINT							#
#===============================================#
source -echo -verbose ./DATA/constraints.tcl


set_operating_conditions -max $LIB_WC_OPCON -max_library $LIB_WC_NAME \
		                 -min $LIB_WC_OPCON -min_library $LIB_BC_NAME


set_fix_multiple_port_nets -all -buffer_constants


current_design $TOP_LEVEL
set_max_area  0.0
set_flatten false
set_structure true -timing true -boolean false


#compile_ultra       -area_high_effort_script -no_autoungroup -no_boundary_optimization
compile -map_effort high



redirect -file ./result/report.timing			{report_timing}
redirect -file ./result/report.clock_tree		{report_clock_tree}

redirect -file ./result/check.timing			{check_timing}
redirect -file ./result/report.constraints		{report_constraints -all_violators -verbose}
redirect -file ./result/report.paths.max		{report_timing -path end  -delay max -max_paths 200 -nworst 2}
redirect -file ./result/report.full_paths.max 	{report_timing -path full -delay max -max_paths 5   -nworst 2}
redirect -file ./result/report.paths.min      	{report_timing -path end  -delay min -max_paths 200 -nworst 2}
redirect -file ./result/report.full_paths.min 	{report_timing -path full -delay min -max_paths 5   -nworst 2}
redirect -file ./result/report.refs           	{report_reference}
redirect -file ./result/report.area           	{report_area}

if {[info exists NAND2_NAME]} {
    set nand2_area [get_attribute [get_lib_cell $LIB_WC_NAME/$NAND2_NAME] area]
    redirect -variable area {report_area}
    regexp {Total cell area:\s+([^\n]+)\n} $area whole_match area
    set nand2_eq [expr $area/$nand2_area]
    set fp [open "./result/report.area" a]
    puts $fp ""
    puts $fp "NAND2 equivalent cell area: $nand2_eq"
    close $fp
    puts ""
    puts "      ======================================================="
    puts "     |                       AREA SUMMARY                    "
    puts "     |-------------------------------------------------------"
    puts "     |"
    puts "     |    $NAND2_NAME cell gate area: $nand2_area"
    puts "     |"
    puts "     |    Total Area                : $area"
    puts "     |    NAND2 equivalent cell area: $nand2_eq"
    puts "     |"
    puts "      ======================================================="
    puts ""
}

current_design $TOP_LEVEL

change_name -rules verilog -hierarchy

write -hierarchy -format verilog -output "./result/$TOP_LEVEL.gate.v"
write -hierarchy -format ddc     -output "./result/$TOP_LEVEL.ddc"
write_sdf -version 2.1 "./result/$TOP_LEVEL.gln.sdf"
write_sdc "./result/$TOP_LEVEL.gln.sdc"

quit

