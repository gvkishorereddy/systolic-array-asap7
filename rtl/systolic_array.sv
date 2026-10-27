`timescale 1ns/1ps
`default_nettype none
// Related reference: https://gitlab.symbioticeda.com/rakshithsuresh2001/systolic_array
// Reference author: Rakshith Suresh (8x8 weight-stationary architecture).
// This is a separately written 4x4 output-stationary implementation.
// The reference project's PPA results do not describe this implementation.
// 4x4 signed INT8 matrix multiply, C=A*B, with 32-bit accumulators.
// Row-major operand storage; writes and starts are ignored while busy.
// start wins over load_en when both are asserted during idle.
module systolic_array (
    input wire clk,
    input wire rst_n,
    input wire load_en,
    input wire load_b,
    input wire [3:0] load_addr,
    input wire signed [7:0] load_data,
    input wire start,
    input wire [3:0] result_addr,
    output wire signed [31:0] result_data,
    output reg busy,
    output reg done
);
    reg signed [7:0] a_mem [0:15];
    reg signed [7:0] b_mem [0:15];
    reg [3:0] step;
    wire clear = start && !busy;
    wire signed [7:0] a_bus [0:3][0:4];
    wire signed [7:0] b_bus [0:4][0:3];
    wire signed [31:0] sums [0:15];
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0;
            done <= 0;
            step <= 0;
            for (i=0; i<16; i=i+1) begin
                a_mem[i] <= 0;
                b_mem[i] <= 0;
            end
        end else begin
            done <= 0;
            if (busy) begin
                if (step == 4'd9) begin
                    busy <= 0;
                    done <= 1;
                    step <= 0;
                end else begin
                    step <= step + 1'b1;
                end
            end else if (start) begin
                busy <= 1;
                step <= 0;
            end else if (load_en) begin
                if (load_b) b_mem[load_addr] <= load_data;
                else a_mem[load_addr] <= load_data;
            end
        end
    end
    genvar r, c;
    generate
        for (r=0; r<4; r=r+1) begin: rows
            // Boundary skew: A[r,k] enters on step k+r.
            assign a_bus[r][0] = (int'(step)>=r && int'(step)<r+4)
                ? a_mem[r*4+int'(step)-r] : 8'sd0;
            for (c=0; c<4; c=c+1) begin: cols
                mac_pe pe (
                    .clk(clk), .rst_n(rst_n), .clear(clear), .enable(busy),
                    .a_in(a_bus[r][c]), .b_in(b_bus[r][c]),
                    .a_out(a_bus[r][c+1]), .b_out(b_bus[r+1][c]),
                    .acc(sums[r*4+c])
                );
            end
        end
        for (c=0; c<4; c=c+1) begin: inputs_b
            // Boundary skew: B[k,c] enters on step k+c.
            assign b_bus[0][c] = (int'(step)>=c && int'(step)<c+4)
                ? b_mem[(int'(step)-c)*4+c] : 8'sd0;
        end
    endgenerate
    assign result_data = sums[result_addr];
endmodule
`default_nettype wire
