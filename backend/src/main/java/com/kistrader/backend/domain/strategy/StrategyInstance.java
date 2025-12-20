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

import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "strategy_instances")
public class StrategyInstance extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "template_id")
    private StrategyTemplate template;

    private String name;

    @Column(columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private JsonNode params;

    @Column(name = "is_active")
    private Boolean isActive;

    private LocalDateTime lastRunAt;

    @Builder
    public StrategyInstance(User user, StrategyTemplate template, String name, JsonNode params, Boolean isActive) {
        this.user = user;
        this.template = template;
        this.name = name;
        this.params = params;
        this.isActive = isActive != null ? isActive : false;
    }

    public void updateLastRun(LocalDateTime time) {
        this.lastRunAt = time;
    }
}
