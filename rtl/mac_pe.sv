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
    input wire weight_we,
    input wire signed [DATA_WIDTH-1:0] weight_data,
    input wire signed [DATA_WIDTH-1:0] a_in,
    output reg signed [DATA_WIDTH-1:0] a_out,
    input wire signed [ACC_WIDTH-1:0] psum_in,
    output reg signed [ACC_WIDTH-1:0] psum_out
);
    reg signed [DATA_WIDTH-1:0] weight;
    wire signed [2*DATA_WIDTH-1:0] product = a_in * weight;
    wire signed [ACC_WIDTH-1:0] extended_product =
        {{(ACC_WIDTH-2*DATA_WIDTH){product[2*DATA_WIDTH-1]}}, product};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_out <= 0;
            psum_out <= 0;
            weight <= 0;
        end else begin
            if (weight_we) weight <= weight_data;
            if (clear) begin
                a_out <= 0;
                psum_out <= 0;
            end else if (enable) begin
                a_out <= a_in;
                psum_out <= psum_in + extended_product;
            end
        end
    end
endmodule
`default_nettype wire
