package com.kistrader.backend.service;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

import java.util.Map;

@FeignClient(name = "liveEngine", url = "${engine.live-url}")
public interface LiveEngineFeignClient {

    @GetMapping("/health")
    Map<String, Object> health();

    @GetMapping("/price/{ticker}")
    Map<String, Object> getPrice(@PathVariable("ticker") String ticker);

    @PostMapping("/order")
    Map<String, Object> placeOrder(@RequestBody Map<String, Object> orderRequest);

    @GetMapping("/balance")
    Map<String, Object> getBalance();
}
