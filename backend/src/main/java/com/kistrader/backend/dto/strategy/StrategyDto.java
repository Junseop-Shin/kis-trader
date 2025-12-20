package com.kistrader.backend.dto.strategy;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

public class StrategyDto {

    @Data
    public static class CreateTemplateRequest {
        private String name;
        private String description;
        private JsonNode reactFlowData;
    }

    @Data
    public static class TemplateResponse {
        private Long id;
        private String name;
        private String description;
        private JsonNode reactFlowData;
        private String createdAt;

        public TemplateResponse(Long id, String name, String description, JsonNode reactFlowData, String createdAt) {
            this.id = id;
            this.name = name;
            this.description = description;
            this.reactFlowData = reactFlowData;
            this.createdAt = createdAt;
        }
    }
}
