set CLOCK_PERIOD ; #(ns) 
set CLOCK_NAME ""

create_clock -name $CLOCK_NAME									\
			 -period "$CLOCK_PERIOD"							
			 

set_drive 0 $CLOCK_NAME

set_clock_uncertainty -setup 0 $CLOCK_NAME
set_clock_uncertainty -hold 0 $CLOCK_NAME
#set_clock_latency -source 0.1 $CLOCK_NAME
set_clock_latency -max 0 $CLOCK_NAME
set_clock_transition 0 $CLOCK_NAME

set_input_delay  [expr ($CLOCK_PERIOD*0/100) ] -max -clock $CLOCK_NAME [all_inputs]
set_input_delay  0		-min -clock $CLOCK_NAME [get_ports input_pin_A]
#set_load 0.020 [all_inputs]
#set_load pF [port]


set_output_delay [expr ($CLOCK_PERIOD*0/100) ] -max -clock $CLOCK_NAME [all_outputs]
set_output_delay 0		-min -clock $CLOCK_NAME [get_ports output_pin_A]
set_load 100 [all_outputs]

set_max_fanout 0 [find design *]



