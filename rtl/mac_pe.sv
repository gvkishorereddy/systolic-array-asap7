`timescale 1ns/1ps
`default_nettype none
module mac_pe #(
    parameter integer DATA_WIDTH = 8,
    parameter integer ACC_WIDTH = 32
) (
    input wire clk,
    input wire rst_n,
    input wire clear,
    input wire enable,
    input wire signed [DATA_WIDTH-1:0] a_in,
    input wire signed [DATA_WIDTH-1:0] b_in,
    output reg signed [DATA_WIDTH-1:0] a_out,
    output reg signed [DATA_WIDTH-1:0] b_out,
    output reg signed [ACC_WIDTH-1:0] acc
);
    wire signed [2*DATA_WIDTH-1:0] product = a_in * b_in;
    wire signed [ACC_WIDTH-1:0] extended_product =
        {{(ACC_WIDTH-2*DATA_WIDTH){product[2*DATA_WIDTH-1]}}, product};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_out <= 0;
            b_out <= 0;
            acc <= 0;
        end else if (clear) begin
            a_out <= 0;
            b_out <= 0;
            acc <= 0;
        end else if (enable) begin
            a_out <= a_in;
            b_out <= b_in;
            acc <= acc + extended_product;
        end
    end
endmodule
`default_nettype wire
