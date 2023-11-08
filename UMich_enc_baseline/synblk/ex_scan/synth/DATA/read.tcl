set TOP_LEVEL      ""

set SOURCE_FILES {
#set your verilog file. location/source.v	
}

set_svf ./result/$TOP_LEVEL.svf
define_design_lib WORK -path ./WORK
analyze -format verilog $SOURCE_FILES

#'elaborate' command automatically executes the 'link' command.
elaborate $TOP_LEVEL -architecture verilog 
#link

#read_verilog ./src/DLDO.v
#set_dont_touch {not_u0 not_u1 not_u2 and_u0 and_u1 y1 y2 y3}
#set_dont_touch not_u0
#set_dont_touch not_u1
#set_dont_touch not_u2
#set_dont_touch and_u0
#set_dont_touch and_u1

#uniquify

#link

# Check design structure after reading verilog
current_design $TOP_LEVEL


redirect -file ./result/report.check {check_design}

