package com.kistrader.backend.domain.price;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "daily_prices", indexes = {
        @Index(name = "idx_daily_prices_date", columnList = "date"),
        @Index(name = "idx_daily_prices_ticker_date", columnList = "ticker, date")
})
// Ideally, table partitioning by RANGE (date) should be applied in DDL.
// Example: CREATE TABLE daily_prices ... PARTITION BY RANGE (date);
public class DailyPrice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String ticker;

    @Column(nullable = false)
    private LocalDate date;

    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Long volume;

    @Builder
    public DailyPrice(String ticker, LocalDate date, BigDecimal open, BigDecimal high, BigDecimal low, BigDecimal close,
            Long volume) {
        this.ticker = ticker;
        this.date = date;
        this.open = open;
        this.high = high;
        this.low = low;
        this.close = close;
        this.volume = volume;
    }
}
