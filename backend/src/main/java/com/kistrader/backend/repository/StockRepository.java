package com.kistrader.backend.repository;

import com.kistrader.backend.domain.Stock;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface StockRepository extends JpaRepository<Stock, String> {
    Optional<Stock> findByTicker(String ticker);
}
