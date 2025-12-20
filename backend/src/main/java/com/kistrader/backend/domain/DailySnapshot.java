package com.kistrader.backend.domain;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "daily_snapshots")
public class DailySnapshot {

    @Id
    private LocalDate date;

    private BigDecimal totalAsset;
    private BigDecimal cash;
    private BigDecimal holdingsValue;

    @Builder
    public DailySnapshot(LocalDate date, BigDecimal totalAsset, BigDecimal cash, BigDecimal holdingsValue) {
        this.date = date;
        this.totalAsset = totalAsset;
        this.cash = cash;
        this.holdingsValue = holdingsValue;
    }
}
