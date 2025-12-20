package com.kistrader.backend.service;

import com.kistrader.backend.domain.strategy.StrategyTemplate;
import com.kistrader.backend.domain.user.User;
import com.kistrader.backend.dto.strategy.StrategyDto;
import com.kistrader.backend.repository.StrategyTemplateRepository;
import com.kistrader.backend.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class StrategyService {

    private final StrategyTemplateRepository templateRepository;
    private final UserRepository userRepository;

    @Transactional
    public Long createTemplate(StrategyDto.CreateTemplateRequest request) {
        User user = getCurrentUser();

        StrategyTemplate template = StrategyTemplate.builder()
                .user(user)
                .name(request.getName())
                .description(request.getDescription())
                .reactFlowData(request.getReactFlowData())
                .build();

        return templateRepository.save(template).getId();
    }

    @Transactional(readOnly = true)
    public List<StrategyDto.TemplateResponse> getMyTemplates() {
        User user = getCurrentUser();
        return templateRepository.findAllByUserId(user.getId()).stream()
                .map(t -> new StrategyDto.TemplateResponse(
                        t.getId(),
                        t.getName(),
                        t.getDescription(),
                        t.getReactFlowData(),
                        t.getCreatedAt().toString()))
                .collect(Collectors.toList());
    }

    private User getCurrentUser() {
        Object principal = SecurityContextHolder.getContext().getAuthentication().getPrincipal();
        String email;
        if (principal instanceof UserDetails) {
            email = ((UserDetails) principal).getUsername();
        } else {
            email = principal.toString();
        }
        return userRepository.findByEmail(email)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));
    }
}
