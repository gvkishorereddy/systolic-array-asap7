`timescale 1ns/1ps
module tb_systolic;
    reg clk = 0;
    always #10 clk = ~clk; // Stimulus clock, NOT a claim about physical Fmax.
    reg rst_n = 0, load_en = 0, load_b = 0, start = 0;
    reg [3:0] load_addr = 0, result_addr = 0;
    reg signed [7:0] load_data = 0;
    wire signed [31:0] result_data;
    wire busy, done;
    reg [767:0] vectors [0:255];
    integer t, j, k, cycles, checks=0, matrices=0;
    reg signed [31:0] expected;
    systolic_array dut(.*);
    task reset_dut;
        begin
            @(negedge clk); rst_n=0; start=0; load_en=0;
            repeat (2) @(negedge clk);
            rst_n=1;
            @(posedge clk); #1;
            if (busy !== 0 || done !== 0 || result_data !== 0)
                $fatal(1, "reset failed");
        end
    endtask
    task load_operands(input integer v);
        begin
            for (k=0;k<32;k=k+1) begin
                @(negedge clk);
                load_en=1; load_b=(k>=16); load_addr=4'(k%16);
                load_data = vectors[v][(k*8)+:8];
            end
            @(negedge clk); load_en=0;
        end
    endtask
    initial begin
        $readmemh("build/vectors.hex",vectors);
        if ($test$plusargs("vcd")) begin
            $dumpfile("build/systolic.vcd");
            $dumpvars(0,tb_systolic);
        end
        reset_dut();
        // Check asynchronous reset also aborts an in-flight operation.
        load_operands(5);
        start=1; @(negedge clk); start=0;
        repeat (3) @(negedge clk);
        reset_dut();
        for(t=0;t<256;t=t+1) begin
            load_operands(t);
            start=1;
            @(posedge clk); #1;
            if (!busy || done) $fatal(1,"start handshake failed");
            @(negedge clk); start=0;
            cycles=0;
            while (!done) begin
                // Input writes and start requests while busy must be ignored.
                if (cycles==2) begin
                    start=1; load_en=1; load_addr=0; load_data=8'sd99;
                end else begin start=0; load_en=0; end
                @(posedge clk); #1;
                cycles=cycles+1;
                if (cycles>10) $fatal(1,"completion timeout at vector %0d",t);
                @(negedge clk);
            end
            start=0; load_en=0;
            if(cycles!=10 || busy) $fatal(1,"latency/busy error: %0d",cycles);
            for(j=0;j<16;j=j+1) begin
                result_addr=4'(j); #1;
                expected=$signed(vectors[t][256+j*32+:32]);
                if(result_data !== expected)
                    $fatal(1,"vector=%0d element=%0d got=%0d expected=%0d",t,j,result_data,expected);
                checks=checks+1;
            end
            @(posedge clk); #1;
            if(done || busy) $fatal(1,"done must be a one-cycle pulse");
            matrices=matrices+1;
        end
        $display("PASS matrices=%0d output_checks=%0d compute_cycles=10 seed=20261027",matrices,checks);
        $display("PASS control: reset, reset-during-compute, busy-write/start rejection, repeated operations, done pulse");
        $finish;
    end
    initial begin
        #10000000; $fatal(1,"global watchdog");
    end
endmodule
