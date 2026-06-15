package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 处置方案 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TreatmentPlanSchema {

    @JsonProperty("plan_name")
    private Object planName;

    @JsonProperty("steps")
    private List<TreatmentStepSchema> steps;

    @JsonProperty("materials")
    private Object materials;

    @JsonProperty("estimated_cost")
    private Object estimatedCost;

    @JsonProperty("difficulty_level")
    private Object difficultyLevel;

    @JsonProperty("personnel_required")
    private Object personnelRequired;

    public Object getPlanName() {
        return planName;
    }

    public void setPlanName(Object planName) {
        this.planName = planName;
    }

    public List<TreatmentStepSchema> getSteps() {
        return steps;
    }

    public void setSteps(List<TreatmentStepSchema> steps) {
        this.steps = steps;
    }

    public Object getMaterials() {
        return materials;
    }

    public void setMaterials(Object materials) {
        this.materials = materials;
    }

    public Object getEstimatedCost() {
        return estimatedCost;
    }

    public void setEstimatedCost(Object estimatedCost) {
        this.estimatedCost = estimatedCost;
    }

    public Object getDifficultyLevel() {
        return difficultyLevel;
    }

    public void setDifficultyLevel(Object difficultyLevel) {
        this.difficultyLevel = difficultyLevel;
    }

    public Object getPersonnelRequired() {
        return personnelRequired;
    }

    public void setPersonnelRequired(Object personnelRequired) {
        this.personnelRequired = personnelRequired;
    }

}