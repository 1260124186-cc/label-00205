package com.boltprediction.sdk.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;
import java.time.OffsetDateTime;

/** 工况信息 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class WorkingConditionSchema {

    @JsonProperty("temperature")
    private Object temperature;

    @JsonProperty("pressure")
    private Object pressure;

    @JsonProperty("humidity")
    private Object humidity;

    @JsonProperty("vibration")
    private Object vibration;

    @JsonProperty("load_condition")
    private Object loadCondition;

    @JsonProperty("operating_hours")
    private Object operatingHours;

    @JsonProperty("maintenance_cycle")
    private Object maintenanceCycle;

    @JsonProperty("last_maintenance_date")
    private Object lastMaintenanceDate;

    @JsonProperty("equipment_age")
    private Object equipmentAge;

    @JsonProperty("extra")
    private Object extra;

    public Object getTemperature() {
        return temperature;
    }

    public void setTemperature(Object temperature) {
        this.temperature = temperature;
    }

    public Object getPressure() {
        return pressure;
    }

    public void setPressure(Object pressure) {
        this.pressure = pressure;
    }

    public Object getHumidity() {
        return humidity;
    }

    public void setHumidity(Object humidity) {
        this.humidity = humidity;
    }

    public Object getVibration() {
        return vibration;
    }

    public void setVibration(Object vibration) {
        this.vibration = vibration;
    }

    public Object getLoadCondition() {
        return loadCondition;
    }

    public void setLoadCondition(Object loadCondition) {
        this.loadCondition = loadCondition;
    }

    public Object getOperatingHours() {
        return operatingHours;
    }

    public void setOperatingHours(Object operatingHours) {
        this.operatingHours = operatingHours;
    }

    public Object getMaintenanceCycle() {
        return maintenanceCycle;
    }

    public void setMaintenanceCycle(Object maintenanceCycle) {
        this.maintenanceCycle = maintenanceCycle;
    }

    public Object getLastMaintenanceDate() {
        return lastMaintenanceDate;
    }

    public void setLastMaintenanceDate(Object lastMaintenanceDate) {
        this.lastMaintenanceDate = lastMaintenanceDate;
    }

    public Object getEquipmentAge() {
        return equipmentAge;
    }

    public void setEquipmentAge(Object equipmentAge) {
        this.equipmentAge = equipmentAge;
    }

    public Object getExtra() {
        return extra;
    }

    public void setExtra(Object extra) {
        this.extra = extra;
    }

}