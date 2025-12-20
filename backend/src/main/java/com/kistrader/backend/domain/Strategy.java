package com.kistrader.backend.domain;

import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.util.Map;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Table(name = "strategies")
public class Strategy extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> params;

    private boolean isActive;

    @Builder
    public Strategy(String name, Map<String, Object> params, boolean isActive) {
        this.name = name;
        this.params = params;
        this.isActive = isActive;
    }
    
    public void updateStatus(boolean isActive) {
        this.isActive = isActive;
    }
}
