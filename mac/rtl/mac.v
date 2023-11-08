module mac (
    CLK,
    nRESET,

    INA,
    INB,
    OUT 
);

input               CLK;
input               nRESET;
input       [15:0]  INA;
input       [15:0]  INB;

output  reg [31:0]  OUT;

always @(posedge CLK or negedge nRESET)
begin
    if (!nRESET)
    begin
        OUT     <= 32'd0;
    end 
    else
    begin
        OUT     <= OUT + (INA*INB);
    end 
end

endmodule
