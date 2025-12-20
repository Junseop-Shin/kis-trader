package com.kistrader.backend.repository;

import com.kistrader.backend.domain.strategy.StrategyInstance;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StrategyInstanceRepository extends JpaRepository<StrategyInstance, Long> {
    List<StrategyInstance> findAllByUserId(Long userId);
}
