package com.kistrader.backend.repository;

import com.kistrader.backend.domain.price.DailyPrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;

@Repository
public interface DailyPriceRepository extends JpaRepository<DailyPrice, Long> {
    Optional<DailyPrice> findByTickerAndDate(String ticker, LocalDate date);
}
