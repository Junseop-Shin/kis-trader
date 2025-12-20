package com.kistrader.backend.domain.strategy;

import com.fasterxml.jackson.databind.JsonNode;
import com.kistrader.backend.domain.BaseTimeEntity;
import com.kistrader.backend.domain.user.User;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "strategy_templates")
public class StrategyTemplate extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id") // NULL if system template
    private User user;

    @Column(nullable = false)
    private String name;

    @Column(columnDefinition = "TEXT")
    private String description;

    @Column(name = "react_flow_data", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private JsonNode reactFlowData; // Using JsonNode for flexible structure

    @Builder
    public StrategyTemplate(User user, String name, String description, JsonNode reactFlowData) {
        this.user = user;
        this.name = name;
        this.description = description;
        this.reactFlowData = reactFlowData;
    }
}
