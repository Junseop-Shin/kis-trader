package com.kistrader.backend.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.util.Map;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "backtest_reports")
public class BacktestReport extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "strategy_id")
    private Strategy strategy;

    private String period; // e.g. "20230101-20231231"

    private BigDecimal mdd;
    private BigDecimal roi;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> chartData;

    @Builder
    public BacktestReport(Strategy strategy, String period, BigDecimal mdd, BigDecimal roi, Map<String, Object> chartData) {
        this.strategy = strategy;
        this.period = period;
        this.mdd = mdd;
        this.roi = roi;
        this.chartData = chartData;
    }
}
