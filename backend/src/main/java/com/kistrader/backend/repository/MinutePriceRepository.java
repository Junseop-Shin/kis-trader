package com.kistrader.backend.repository;

import com.kistrader.backend.domain.price.MinutePrice;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MinutePriceRepository extends JpaRepository<MinutePrice, Long> {
}
