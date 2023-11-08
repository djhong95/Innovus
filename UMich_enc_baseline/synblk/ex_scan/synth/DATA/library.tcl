set abs_dir ""

# Define worst case library
set LIB_WC_FILE   "${abs_dir}/"
set LIB_WC_NAME   "${abs_dir}/"

# Define best case library
set LIB_BC_FILE   "${abs_dir}/"
set LIB_BC_NAME   "${abs_dir}/"

# Define operating conditions
set LIB_WC_OPCON  ""
set LIB_BC_OPCON  ""

# Define wire-load model
#set LIB_WIRE_LOAD "<YOUR WIRE LOAD MODEL>"

# Define nand2 gate name for aera size calculation
set NAND2_NAME    ""


# Set library
set target_library $LIB_WC_FILE
set link_library   $LIB_WC_FILE
set_min_library    $LIB_WC_FILE  -min_version $LIB_BC_FILE
