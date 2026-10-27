`timescale 1ns/1ps
`default_nettype none
// Independently reconstructed 8x8 signed INT8 implementation, C=A*B.
// Owner-reported physical metrics are from an earlier run, not this RTL.
// B[k,c] is stationary in PE[k,c]. A[r,k] enters row k on cycle r+k.
// Activations move right and partial sums move down, one hop per cycle.
module systolic_array (
    input wire clk,
    input wire rst_n,
    input wire load_en,
    input wire load_b,
    input wire [5:0] load_addr,
    input wire signed [7:0] load_data,
    input wire start,
    input wire [5:0] result_addr,
    output wire signed [31:0] result_data,
    output reg busy,
    output reg done
);
    localparam integer N = 8;
    // Last valid PE output is produced on step 3*N-3 and captured next cycle.
    localparam integer LAST_STEP = 3*N-2;
    reg signed [7:0] a_mem [0:N*N-1];
    reg signed [31:0] result_mem [0:N*N-1];
    reg [5:0] step;
    wire clear = start && !busy;
    wire signed [7:0] a_bus [0:N-1][0:N];
    wire signed [31:0] psum_bus [0:N][0:N-1];
    integer i, j;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0;
            done <= 0;
            step <= 0;
            for (i=0; i<N*N; i=i+1) begin
                a_mem[i] <= 0;
                result_mem[i] <= 0;
            end
        end else begin
            done <= 0;
            if (busy) begin
                for (j=0; j<N; j=j+1) begin
                    if (int'(step)>=N+j && int'(step)<2*N+j)
                        result_mem[(int'(step)-N-j)*N+j] <= psum_bus[N][j];
                end
                if (step == LAST_STEP) begin
                    busy <= 0;
                    done <= 1;
                    step <= 0;
                end else begin
                    step <= step + 1'b1;
                end
            end else if (start) begin
                busy <= 1;
                step <= 0;
                for (i=0; i<N*N; i=i+1) result_mem[i] <= 0;
            end else if (load_en && !load_b) begin
                a_mem[load_addr] <= load_data;
            end
        end
    end
    genvar k, c;
    generate
        for (k=0; k<N; k=k+1) begin: rows
            assign a_bus[k][0] = (int'(step)>=k && int'(step)<k+N)
                ? a_mem[(int'(step)-k)*N+k] : 8'sd0;
            for (c=0; c<N; c=c+1) begin: cols
                mac_pe pe (
                    .clk(clk), .rst_n(rst_n), .clear(clear), .enable(busy),
                    .weight_we(load_en && load_b && !busy && !start && load_addr==k*N+c),
                    .weight_data(load_data),
                    .a_in(a_bus[k][c]), .a_out(a_bus[k][c+1]),
                    .psum_in(psum_bus[k][c]), .psum_out(psum_bus[k+1][c])
                );
            end
        end
        for (c=0; c<N; c=c+1) begin: psum_inputs
            assign psum_bus[0][c] = 32'sd0;
        end
    endgenerate
    assign result_data = result_mem[result_addr];
endmodule
`default_nettype wire
