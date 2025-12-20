package com.kistrader.backend.domain.order;

import com.kistrader.backend.domain.BaseTimeEntity;
import com.kistrader.backend.domain.strategy.StrategyInstance;
import com.kistrader.backend.domain.user.User;
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
@Table(name = "trade_orders")
public class TradeOrder extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "instance_id")
    private StrategyInstance instance;

    @Column(nullable = false)
    private String ticker;

    @Enumerated(EnumType.STRING)
    private OrderType orderType; // BUY, SELL

    private BigDecimal price;
    private Integer quantity;

    @Column(columnDefinition = "numeric(19,2) default 0")
    private BigDecimal fee;

    @Enumerated(EnumType.STRING)
    private OrderStatus status; // PENDING, FILLED, REJECTED

    @Enumerated(EnumType.STRING)
    private OrderMode mode; // LIVE, PAPER

    private LocalDateTime filledAt;

    @Builder
    public TradeOrder(User user, StrategyInstance instance, String ticker, OrderType orderType, BigDecimal price,
            Integer quantity, OrderMode mode) {
        this.user = user;
        this.instance = instance;
        this.ticker = ticker;
        this.orderType = orderType;
        this.price = price;
        this.quantity = quantity;
        this.mode = mode != null ? mode : OrderMode.PAPER;
        this.status = OrderStatus.PENDING;
    }

    public enum OrderType {
        BUY, SELL
    }

    public enum OrderStatus {
        PENDING, FILLED, REJECTED, CANCELLED
    }

    public enum OrderMode {
        LIVE, PAPER
    }
}
