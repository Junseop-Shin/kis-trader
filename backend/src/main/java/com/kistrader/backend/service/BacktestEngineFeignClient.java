package com.kistrader.backend.service;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.Map;

@FeignClient(name = "backtestEngine", url = "${engine.backtest-url}")
public interface BacktestEngineFeignClient {

    @GetMapping("/health")
    Map<String, Object> health();

    @PostMapping("/backtest")
    Map<String, Object> runBacktest(@RequestBody Map<String, Object> backtestRequest);
}
