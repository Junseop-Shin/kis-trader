package com.kistrader.backend.service;

import com.kistrader.backend.domain.user.User;
import com.kistrader.backend.dto.strategy.StrategyDto;
import com.kistrader.backend.repository.StrategyTemplateRepository;
import com.kistrader.backend.repository.UserRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Optional;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

@ExtendWith(MockitoExtension.class)
class StrategyServiceTest {

    @InjectMocks
    private StrategyService strategyService;

    @Mock
    private StrategyTemplateRepository templateRepository;

    @Mock
    private UserRepository userRepository;

    @Test
    @DisplayName("전략_템플릿_생성_성공")
    void create_template_success() {
        // given
        StrategyDto.CreateTemplateRequest request = new StrategyDto.CreateTemplateRequest();
        request.setName("My Strategy");
        request.setDescription("Test Desc");

        // Mock Security Context
        Authentication authentication = mock(Authentication.class);
        SecurityContext securityContext = mock(SecurityContext.class);
        given(securityContext.getAuthentication()).willReturn(authentication);
        given(authentication.getPrincipal()).willReturn("user@test.com");
        SecurityContextHolder.setContext(securityContext);

        User mockUser = User.builder().email("user@test.com").build();
        given(userRepository.findByEmail("user@test.com")).willReturn(Optional.of(mockUser));

        given(templateRepository.save(any())).willAnswer(invocation -> invocation.getArgument(0));

        // when
        strategyService.createTemplate(request);

        // then
        verify(templateRepository).save(any());
        verify(userRepository).findByEmail("user@test.com");
    }
}
