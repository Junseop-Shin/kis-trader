package com.kistrader.backend.controller;

import com.kistrader.backend.dto.strategy.StrategyDto;
import com.kistrader.backend.service.StrategyService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/strategies")
@RequiredArgsConstructor
public class StrategyController {

    private final StrategyService strategyService;

    @PostMapping("/templates")
    public ResponseEntity<Long> createTemplate(@RequestBody StrategyDto.CreateTemplateRequest request) {
        return ResponseEntity.ok(strategyService.createTemplate(request));
    }

    @GetMapping("/templates")
    public ResponseEntity<List<StrategyDto.TemplateResponse>> getMyTemplates() {
        return ResponseEntity.ok(strategyService.getMyTemplates());
    }
}
