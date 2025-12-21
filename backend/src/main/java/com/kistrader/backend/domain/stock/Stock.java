package com.kistrader.backend.domain.stock;

import com.kistrader.backend.domain.BaseTimeEntity;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "stocks")
public class Stock extends BaseTimeEntity {

    @Id
    private String ticker; // e.g., "005930"

    private String name; // e.g., "Samsung Electronics"

    private String marketType; // KOSPI, KOSDAQ

    @Builder
    public Stock(String ticker, String name, String marketType) {
        this.ticker = ticker;
        this.name = name;
        this.marketType = marketType;
    }
}
