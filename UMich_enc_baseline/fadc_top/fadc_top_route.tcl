


setNanoRouteMode -routeWithViaInPin true
setNanoRouteMode -routeWithViaOnlyForStandardCellPin false
#setNanoRouteMode -routeWithViaOnlyForStandardCellPin true
setNanoRouteMode -routeWithTimingDriven true
setNanoRouteMode -routeWithSiDriven true
setNanoRouteMode -drouteAutoStop false
setNanoRouteMode -drouteUseMinSpacingForBlockage false
setNanoRouteMode -routeMergeSpecialWire true
setNanoRouteMode -drouteHonorStubRuleForBlockPin true
setNanoRouteMode -drouteUseMinSpacingForBlockage false
setNanoRouteMode -drouteUseMultiCutViaEffort high
setNanoRouteMode -routeTopRoutingLayer 4
setNanoRouteMode -routeBottomRoutingLayer 1
setNanoRouteMode -drouteElapsedtimeLimit 1 

#setNanoRouteMode -routeInsertAntennaDiode true
#setNanoRouteMode -routeAntennaCellName "ANTENNA"
placeDesign
globalDetailRoute
#optDesign -postRoute
#timeDesign -postRoute

deleteRouteBlk -box 0 0 95 1207  -layer {METAL1 METAL2 METAL4}

