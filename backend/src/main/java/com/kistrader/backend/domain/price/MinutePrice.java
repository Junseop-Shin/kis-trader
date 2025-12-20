package com.kistrader.backend.domain.price;

import com.kistrader.backend.domain.stock.Stock;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "minute_prices", indexes = {
        @Index(name = "idx_minute_prices_datetime", columnList = "datetime"),
        @Index(name = "idx_minute_prices_ticker_dt", columnList = "ticker, datetime")
})
public class MinutePrice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "ticker", nullable = false)
    private Stock stock;

    @Column(nullable = false)
    private LocalDateTime datetime;

    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Long volume;

    @Builder
    public MinutePrice(Stock stock, LocalDateTime datetime, BigDecimal open, BigDecimal high, BigDecimal low,
            BigDecimal close, Long volume) {
        this.stock = stock;
        this.datetime = datetime;
        this.open = open;
        this.high = high;
        this.low = low;
        this.close = close;
        this.volume = volume;
    }
}
