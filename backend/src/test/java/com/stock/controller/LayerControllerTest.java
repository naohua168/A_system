package com.stock.controller;

import com.stock.config.MockWebMvcTest;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@MockWebMvcTest(LayerController.class)
@AutoConfigureMockMvc(addFilters = false)
class LayerControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private JdbcTemplate jdbcTemplate;

    @Test
    @DisplayName("GET /api/layers - 返回全部 6 层数据")
    void testGetAllLayers() throws Exception {
        mockMvc.perform(get("/api/layers")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(6))
                .andExpect(jsonPath("$.data[0].id").value("L1"))
                .andExpect(jsonPath("$.data[5].id").value("L6"));
    }

    @Test
    @DisplayName("GET /api/layers/L1 - 返回 L1 层详情")
    void testGetLayerDetail() throws Exception {
        mockMvc.perform(get("/api/layers/L1")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.id").value("L1"))
                .andExpect(jsonPath("$.data.name").value("数据采集层"))
                .andExpect(jsonPath("$.data.modules").isArray())
                .andExpect(jsonPath("$.data.status").value("completed"));
    }

    @Test
    @DisplayName("GET /api/layers/INVALID - 不存在的层返回 404")
    void testGetLayerDetail_NotFound() throws Exception {
        mockMvc.perform(get("/api/layers/INVALID")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(404));
    }

    @Test
    @DisplayName("GET /api/layers/flows - 返回数据流定义")
    void testGetFlows() throws Exception {
        mockMvc.perform(get("/api/layers/flows")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(6));
    }

    @Test
    @DisplayName("GET /api/layers/health - 返回各层运行状态")
    void testGetHealth() throws Exception {
        mockMvc.perform(get("/api/layers/health")
                        .accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.L1").value("online"))
                .andExpect(jsonPath("$.data.L2").value("online"))
                .andExpect(jsonPath("$.data.L3").value("online"));
    }
}
