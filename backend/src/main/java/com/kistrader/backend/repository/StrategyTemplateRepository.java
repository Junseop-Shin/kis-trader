package com.kistrader.backend.repository;

import com.kistrader.backend.domain.strategy.StrategyTemplate;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface StrategyTemplateRepository extends JpaRepository<StrategyTemplate, Long> {
    List<StrategyTemplate> findAllByUserId(Long userId);
}
