package com.kistrader.backend.domain.user;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "account_history")
public class AccountHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private LocalDate date;

    private BigDecimal totalBalance;
    private BigDecimal cashBalance;

    @Column(columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private JsonNode holdingsSnapshot;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @Builder
    public AccountHistory(User user, LocalDate date, BigDecimal totalBalance, BigDecimal cashBalance,
            JsonNode holdingsSnapshot) {
        this.user = user;
        this.date = date;
        this.totalBalance = totalBalance;
        this.cashBalance = cashBalance;
        this.holdingsSnapshot = holdingsSnapshot;
        this.createdAt = LocalDateTime.now();
    }
}
