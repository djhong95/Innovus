declare_var('DEFAULT_CLK_FREQ', 'default clock frequency of design', type=float, required=True)
declare_var('CLK_FREQ_MAP', 'clock name to clock frequency map', type=dict)
declare_var('DEFAULT_PWR_NET', 'default power net of the design', type=str, default='VDD')
declare_var('DEFAULT_GND_NET', 'default ground net of the design', type=str, default='VSS')

declare_var('MEMORY_CELLS', 'specify cell names of memory blocks in the design (lef/lib/db files will be handled automatically)', type=list)
declare_var('MEMORY_WRAPPER_VLOG_FILES', 'specify wrapper verilog file for memory blocks in the design', type=list)

declare_var('3D_QRC', '3D qrcTechFile for compact2D flow', type=str)
declare_var('3D_GRD', '3D nxtgrd for compact2D flow', type=str)
declare_var('ILV_R', 'resistance of ILVs in (kOhm)', type=float)
declare_var('ILV_C', 'capacitance of ILVs in (pico Farad)', type=float)

declare_var('PNR_NUM_ROUTE_LAYER', '', flows='pnr', type=int)
declare_var('PNR_3D_NUM_ROUTE_LAYERS', 'number of routing layers in each tier', flows='pnr', type=list, default=[])

declare_var('USE_EXT_RC', 'use parasitics from ext flow in sta and emir flow', flows='pnr', type=bool, default=False)
