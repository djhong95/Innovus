# Multi-Core
setMultiCpuUsage -acquireLicense 4

# Specify the name of your toplevel module
set TOP_LEVEL minipuf_ctrl

set init_pwr_net {VDD AVDD VDD_CORE}
set init_gnd_net VSS
set init_lef_file /icas/kits/tsmc180/sc/tcb018gbwp7t_270a/Back_End/lef/tcb018gbwp7t_270a/lef/tcb018gbwp7t_6lm_utm40k.lef
set init_verilog /icas/projects/02_puf/synblk_mini_rev1/minipuf_ctrl/synth/result/${TOP_LEVEL}.gate.v
set init_mmmc_file ./DATA/mmmc.tcl
set init_top_cell minipuf_ctrl
init_design

# Setup design and create floorplan
# -r H/W_ratio core_utilization (distance between PWR ring and DIG ckt T B L R) 
#floorPlan -site core7T -r 0.8 0.15 10 10 10 10
set pwrring_width 3
set pwrring_space 2.5
set pwrstrp_width 3
set pwrstrp_space 2.5

set left_offset   [expr $pwrring_width*4 + 6*$pwrring_space]
set right_offset  [expr $pwrring_width*4 + 6*$pwrring_space]
set top_offset    [expr $pwrring_width*4 + 6*$pwrring_space]
set bottom_offset [expr $pwrring_width*4 + 6*$pwrring_space]

floorPlan -s 432.08 532.08  $left_offset $right_offset $bottom_offset $top_offset
checkFPlan
loadIoFile ./DATA/${TOP_LEVEL}.io
fit

setFlipping s
redraw
fit

# GLOBAL CONNECT ----------------------------------------------------------------------
globalNetConnect VDD      -type pgpin -pin {VDD} -inst {*} -verbose
globalNetConnect VDD 		-type tiehi
#ADD YOUR GROUND CONNECT
saveDesign "${TOP_LEVEL}.globalconnect.enc"

# POWER STRIPES -----------------------------------------------------------------------
#source ../scripts/${TOP_LEVEL}_power.tcl
# ADD Ring
setAddRingMode \
		-stacked_via_top_layer METAL6 \
		-stacked_via_bottom_layer METAL1
addRing \
	-skip_via_on_wire_shape Noshape \
	-skip_via_on_pin Standardcell \
	-type core_rings \
	-jog_distance 0.28 \
	-threshold 0.28 \
	-nets {VSS VDD AVDD VDD_CORE} \
	-follow core \
	-layer {bottom METAL5 top METAL5 right METAL6 left METAL6} \
	-width 3 \
	-spacing 3 \
	-offset 5 \
	-bl 1 -br 1 -tl 1 -tr 1 -rt 1 -rb 1 -lt 1 -lb 1

# Vertical STIRPE
addstripe -nets {VDD VSS} -layer METAL6 -direction vertical -width $pwrstrp_width -spacing $pwrstrp_space -number_of_sets 10 \
     -snap_wire_center_to_grid Grid -xleft_offset 0 -xright_offset 0
# Removing unwanted stripe

#	  -extend_to design_boundary -create_pins 1
sroute -nets {VDD VSS}
#sroute -nets {VDD VSS} -corePinLayer {1 2}

saveDesign "${TOP_LEVEL}.power.enc"

#WELL TAP INSERT

# PLACE DESIGN ---------------------------------------------------------------------------
#source ../scripts/${TOP_LEVEL}_place.tcl
loadIoFile ./DATA/${TOP_LEVEL}.io

#METAL BLOCKING
#Top1
#createRouteBlk -name blk_T1 -layer METAL5 METAL6 -box 108.240 282.365 232.560 294.125
#Top2
#createRouteBlk -name blk_T2 -layer METAL5 METAL6 -box 348.240 286.825 478.220 298.585
#Bot1
#createRouteBlk -name blk_B1 -layer METAL5 METAL6 -box 108.240 140.710 235.410 152.470
#Bot2
#createRouteBlk -name blk_B2 -layer METAL5 METAL6 -box 348.240 140.710 472.560 152.470

# addWellTap -cell NWSX -maxGap 22 -prefix NWSX

setPrerouteAsObs {1 2 3}
timeDesign -prePlace
setPlaceMode -congEffort high -maxRouteLayer 5
setPlaceMode -timingDriven true
placeDesign
congOpt -nrIterInCongOpt 20


#globalNetConnect VDD      -type pgpin -pin {VDD} -inst {*} -module {} 
#globalNetConnect VDD 		-type tiehi
#globalNetConnect VSS      -type pgpin -pin {VSS} -inst {*} -module {}
#globalNetConnect VSS 		-type tielo
applyGlobalNets
saveDesign "${TOP_LEVEL}.placed.enc"


# Clock ----------------------------------------------------------------------------------
#source ../scripts/${TOP_LEVEL}_clock.tcl
#setCTSMode -bottomPreferredLayer 1 -topPreferredLayer 3 -leafBottomPreferredLayer 1 -leafTopPreferredLayer 3
#loadTimingCon "/afs/eecs.umich.edu/vlsida/projects/mm3_node/synth/${TOP_LEVEL}/scan.sdc"
#exec /bin/rm -f ${TOP_LEVEL}.cts
#createClockTreeSpec -output ${TOP_LEVEL}.cts -ignoreDontUse -bufFootprint clkbuf -invFootprint clkinv
#exec sed -i -r "s/^\#ClkGroup*/ClkGroup\n+ SCLK\n+ HCLK\n+ SCLK_2X\n+ SCLK_2Xn/g" ${TOP_LEVEL}.cts
#specifyClockTree -file ${TOP_LEVEL}.cts
#ckSynthesis -rguide cts.rguide -report report.ctsrpt -macromodel report.ctsmdl -fix_added_buffers -forceReconvergent
#optDesign -postCTS
#optDesign -postCTS -hold
#timeDesign -postCTS

#saveDesign "${TOP_LEVEL}.clock.enc"

# Trial Route ----------------------------------------------------------------------------
#source ../scripts/${TOP_LEVEL}_trialroute.tcl
setTrialRouteMode -useM1 true
trialRoute

# Route -----------------------------------------------------------------------------------
#timeDesign -postRoute
setOptMode -fixCap true -fixTran true -fixFanoutLoad false
optDesign -preCTS


createClockTreeSpec -bufferList {CKBD12BWP7T CKND12BWP7T} -file Clock.ctstch
setCTSMode -engine ck
clockDesign -specFile Clock.ctstch -outDir clock_report -fixedInstBeforeCTS

setOptMode -fixCap true -fixTran true -fixFanoutLoad false
optDesign -postCTS
optDesign -postCTS -hold

redraw

routeDesign -globalDetail -viaOpt -wireOpt
saveDesign "${TOP_LEVEL}.routed.enc"

deleteObstruction -all   

# Add filler cells
addFiller -cell ADD_YOUR_FILLER_CELLS_HERE -prefix FILLER -noDRC
applyGlobalNets

# Metal Fill
setMetalFill -preferredDensity 75
addMetalFill -layer {1 2 3 4 5} -area 26.88 26.88 459.20 43.12 

# Save Design
saveDesign "${TOP_LEVEL}.filled.routed.enc"
deleteObstruction -all

#Delete Blocking area
#deleteRouteBlk -name blk_T1
#deleteRouteBlk -name blk_T2
#deleteRouteBlk -name blk_B1
#deleteRouteBlk -name blk_B2

# Output DEF, LEF and GDSII
set dbgLefDefOutVersion 5.5
defout ${TOP_LEVEL}.def  -placement -routing 
lefout ${TOP_LEVEL}.lef
saveNetlist -excludeLeafCell ${TOP_LEVEL}.apr.v
saveNetlist -excludeLeafCell -includePowerGround ${TOP_LEVEL}.apr.pg.v
streamOut ${TOP_LEVEL}.gds \
    -mapFile "/icas/kits/tsmc180/map/tsmc18.map" \
    -libName $TOP_LEVEL \
    -structureName $TOP_LEVEL \
    -stripes 1 \
    -units 2000 \
    -mode ALL

# Generate SDF
setExtractRCMode -detail -relative_c_th 0.01 -total_c_th 0.01 -noReduce -rcdb tap.db -specialNet
extractRC -outfile ${TOP_LEVEL}.cap
rcOut -spf ${TOP_LEVEL}.spf
rcOut -spef ${TOP_LEVEL}.spef

setUseDefaultDelayLimit 10000
delayCal -sdf ${TOP_LEVEL}.apr.sdf

# Run Geometry and Connection checks
verifyGeometry -reportAllCells -viaOverlap -report ${TOP_LEVEL}.geom.rpt
fixVia -minCut 

# Meant for power vias that are just too small
verifyConnectivity -type all -noAntenna -report ${TOP_LEVEL}.conn.rpt

puts "**************************************"
puts "*                                    *"
puts "* Encounter script finished          *"
puts "*                                    *"
puts "**************************************"

redraw





