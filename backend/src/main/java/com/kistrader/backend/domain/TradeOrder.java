package com.kistrader.backend.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "trade_orders")
public class TradeOrder extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String ticker;

    @Enumerated(EnumType.STRING)
    private OrderType type; // BUY, SELL

    private BigDecimal price;

    private String status; // PENDING, FILLED, CANCELLED

    @Enumerated(EnumType.STRING)
    private TradingMode mode; // LIVE, PAPER

    public enum OrderType {
        BUY, SELL
    }

    public enum TradingMode {
        LIVE, PAPER
    }

    @Builder
    public TradeOrder(String ticker, OrderType type, BigDecimal price, String status, TradingMode mode) {
        this.ticker = ticker;
        this.type = type;
        this.price = price;
        this.status = status;
        this.mode = mode;
    }
}
