import pyomo.environ as pyo
from pyomo.environ import value
import math
import pandas as pd
from preprocessing import *

def optimization():

    model = pyo.AbstractModel()
    
    ##### Model Sets #####
    model.t = pyo.Set(ordered = True, initialize=get_t())
    
    
    ##### Model Parameters #####
    
    ## System
    model.demand = pyo.Param(model.t, initialize=dict_demand(get_import('Demand')))  # hourly demand [kW]
     
    ## PV
    model.pv = pyo.Param(model.t, initialize=dict_demand(get_import('PV')))  # PV generation [kW]
        
    ## Storage
    model.storage_cost = pyo.Param(initialize=info_battery('capex'))
    model.inverter_cost = pyo.Param(initialize=info_battery('inverter_cost'))
    model.fixed_cost = pyo.Param(initialize =info_battery('fix'))
    model.eff = pyo.Param(initialize=info_battery('eff'))
    model.sd = pyo.Param(initialize=info_battery('SD'))
    model.life_cal = pyo.Param(initialize=info_battery('calendar'))
    model.life_cyc = pyo.Param(initialize=info_battery('cycle'))
    model.replacement = pyo.Param(initialize=info_battery('replacement'))
    model.inver_life = pyo.Param(initialize=get_prj('project'))
    model.maxPow_bat = pyo.Param(initialize=info_battery('inverter'))
    model.cap_bat = pyo.Param(initialize=info_battery('capacity'))  

    model.grid_connection = pyo.Param(initialize=info_connection('contract'))
    model.dt = pyo.Param(initialize = 0.25)
    model.tou = pyo.Param(initialize=tariff('tou'))
    model.fit = pyo.Param(initialize=tariff('fit'))
    
    ##### Model Variables #####

    # Storage
    model.grid = pyo.Var(model.t, within =pyo.NonNegativeReals)  
    model.g2L = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.g2b = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.pv2L = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.pv2b = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.b2L = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.pv_curt = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.pv_grid = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.b2grid = pyo.Var(model.t, within=pyo.NonNegativeReals)    
    model.grid_export = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.charge = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.discharge = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.batteries = pyo.Var(within=pyo.Integers)

    model.aging_cal = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.aging_cyc = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.batt_health = pyo.Var(model.t, within=pyo.NonNegativeReals, bounds=(0,1))
    model.max_st = pyo.Var(within=pyo.NonNegativeReals)
    model.batt_power = pyo.Var(within=pyo.NonNegativeReals)
    model.p_batt = pyo.Var(model.t, within=pyo.NonNegativeReals) 
    model.e_batt = pyo.Var(model.t, within=pyo.NonNegativeReals)
    model.e_usable = pyo.Var(within=pyo.NonNegativeReals)
    
    model.u = pyo.Var(model.t, within=pyo.Binary)
    
    ##### Model Constraints #####
    
    
    ## Grid import power flow

    def Constraint_grid(model, t):
        return model.grid[t] == model.g2L[t] + model.g2b[t]
    model.constr_grid = pyo.Constraint(model.t, rule=Constraint_grid)
    
    def Constraint_grid_export(model, t):
        return model.grid_export[t] == model.pv_grid[t] + model.b2grid[t]
    model.constr_grid_export = pyo.Constraint(model.t, rule=Constraint_grid_export)
        
    ## Load power flow
    def Constraint_load(model, t):
        return model.demand[t] == model.pv2L[t]+ model.b2L[t] + model.g2L[t]  
    model.const_load = pyo.Constraint(model.t, rule=Constraint_load)
    
    ## PV power flow
    def Constraint_pv(model, t):
        return model.pv[t] == model.pv2L[t] + model.pv2b[t] + model.pv_grid[t] + model.pv_curt[t] 
    model.constr_pv = pyo.Constraint(model.t, rule=Constraint_pv)
    
    ## charging
    def constraint_charging(model, t):
        return model.charge[t] == model.pv2b[t] + model.g2b[t]
    model.constr_charging = pyo.Constraint(model.t, rule=constraint_charging)
    
    ## Discharging
    def constriant_discharging(model, t):
        return model.discharge[t] == model.b2L[t] + model.b2grid[t]
    model.constr_discharge = pyo.Constraint(model.t, rule=constriant_discharging)
    
    # def balance(model, t):
    #     return model.demand[t] + model.charge[t] + model.grid_export[t] == model.pv[t] + model.discharge[t] + model.grid[t]
    # model.constr_balance = pyo.Constraint(model.t, rule=balance)

    # Contraint to limit the usage of the transformer
    def Constraint_tranf(model, t):
        return model.grid[t] <= model.grid_connection * model.u[t]
    model.constr_connection = pyo.Constraint(model.t, rule=Constraint_tranf)
    
    def Constraint_selling(model, t):
        return model.grid_export[t] <= model.grid_connection * (1-model.u[t])
    model.constr_selling_limit = pyo.Constraint(model.t, rule=Constraint_selling)

    def inverter_power(model, t):
        return model.p_batt[t] == (model.pv2b[t] + model.g2b[t]) * model.eff - ((model.b2L[t] + model.b2grid[t])/model.eff)
    model.constr_battery_power = pyo.Constraint(model.t, rule=inverter_power)
    
    def battery_energy(model, t):
        if t==0:
            return model.e_batt[0] == (model.max_st * 0.95) + (model.eff * model.p_batt[t]*model.dt)
        else:
            return model.e_batt[t] == (model.e_batt[t-1] * (model.sd)) + (model.eff * model.p_batt[t]*model.dt)
    model.constr_ebatt = pyo.Constraint(model.t, rule=battery_energy)
    
    def inverter_charge_limit(model, t):
        return model.charge[t] <= model.batt_power
    model.contr_inverter_charge = pyo.Constraint(model.t, rule=inverter_charge_limit)
    
    def inverter_discharge_limit(model, t):
        return model.discharge[t] <= model.batt_power
    model.constr_inverter_discharge = pyo.Constraint(model.t, rule=inverter_discharge_limit)
    
    def battery_use_range(model):
        return model.e_usable == model.max_st * (0.95-0.1)
    model.constr_usable_battery = pyo.Constraint(rule=battery_use_range)
    
    def battery_energy_limit(model, t):
        return model.e_batt[t] <= model.e_usable * model.batt_health[t]
    model.constr_battery_energy_limit = pyo.Constraint(model.t, rule=battery_energy_limit)
    
    def batt_age_cal(model, t):
        if t == 0:
            return model.aging_cal[t] == 0
        else:
            return model.aging_cal[t] == (t * model.dt)/model.life_cal  
    model.constr_age_cal = pyo.Constraint(model.t, rule=batt_age_cal)
    
    def batt_age_cyc(model, t):
        if t == 0:
            return model.aging_cyc[t] == 0
        else:
            return model.aging_cyc[t] == model.aging_cyc[t-1] + (0.5*model.p_batt[t]*model.dt)/(model.life_cyc*model.e_batt[t])
    model.constr_age_cyc = pyo.Constraint(model.t, rule=batt_age_cyc)
    
    def constr_degradation(model, t):
        if t==0:
            return model.batt_health[0] == 1
        else:
            return model.batt_health[t] == model.batt_health[t-1] - (model.aging_cal[t] + model.aging_cyc[t])*0.2
    model.constr_batt_degradation = pyo.Constraint(model.t, rule=constr_degradation)
    

    
    def func_obj(model):
        
        cost = ((1-model.batt_health[model.t.last()])/(1-model.replacement)) * (model.fixed_cost + model.storage_cost * model.max_st) + model.inverter_cost * model.batt_power * ((model.t.last())/(model.inver_life)*96)
        return sum(model.grid[t]*model.dt*model.tou - model.grid_export[t]*model.dt*model.fit for t in model.t) + cost


    

    ##### Optimization solving #####
    model.goal = pyo.Objective(rule=func_obj, sense=pyo.minimize)
    
    
    ##### Optimization solving #####
    
    instance = model.create_instance()
    opt = pyo.SolverFactory('ipopt')
    results = opt.solve(instance, tee=True)
    post_processing(instance)
    return results

def post_processing(instance):
    

    dict_grid = instance.grid.get_values()
    dict_g2l = instance.g2L.get_values()
    dict_g2b = instance.g2b.get_values()
    dict_pv2l = instance.pv2L.get_values()
    dict_pv2b = instance.pv2b.get_values()
    dict_b2l = instance.b2L.get_values()
    dict_pv_curt = instance.pv_curt.get_values()
    dict_pv_grid = instance.pv_grid.get_values()
    dict_b2grid = instance.b2grid.get_values()
    dict_grid_export = instance.grid_export.get_values()
    
    
    dict_max_st = instance.max_st.get_values()[None]
    dict_battery_power = instance.batt_power.get_values()[None]
    dict_e_usable = instance.e_usable.get_values()[None]
    dict_power = instance.p_batt.get_values()
    dict_energy = instance.e_batt.get_values()
    dict_u=instance.u.get_values()
    
    
    
    
    list_grid = []
    list_u =[]
    list_g2l = []
    list_g2b = []
    list_pv2l = []
    list_pv2b = []
    list_b2l = []
    list_pv_curt = []
    list_pv_grid = []
    list_b2grid = []
    list_grid_export = []
    list_power = []
    list_energy = []
    
    
    for t in lt:
        list_grid.insert(t, dict_grid[t])
        list_u.insert(t, dict_u[t])
        list_g2l.insert(t, dict_g2l[t])
        list_g2b.insert(t, dict_g2b[t])
        list_pv2l.insert(t, dict_pv2l[t])
        list_pv2b.insert(t, dict_pv2b[t])
        list_b2l.insert(t, dict_b2l[t])
        list_b2grid.insert(t, dict_b2grid[t])
        list_pv_curt.insert(t, dict_pv_curt[t])
        list_pv_grid.insert(t, dict_pv_grid[t])
        list_grid_export.insert(t, dict_grid_export[t])
        list_power.insert(t, dict_power[t])
        list_energy.insert(t, dict_energy[t])
        
        
    dict_col_hourly = {}
    dict_col_hourly['Energy_battery'] = list_energy
    dict_col_hourly['Power_Battery'] = list_power
    dict_col_hourly['Grid export'] = list_grid_export
    dict_col_hourly['grid'] = list_grid
    dict_col_hourly['U'] = list_u
    
    
    table_h = pd.DataFrame(dict_col_hourly, index=lt)
    
    dict_col_additional = {}
    dict_col_additional['Grid to Load'] = list_g2l
    dict_col_additional['Grid to battery'] = list_g2b
    dict_col_additional['PV to load'] = list_pv2l
    dict_col_additional['PV to battery'] = list_pv2b
    dict_col_additional['Battery to load'] = list_b2l
    dict_col_additional['Battery to grid'] = list_b2grid
    dict_col_additional['PV_Curtailment'] = list_pv_curt
    dict_col_additional['PV to Grid'] = list_pv_grid
    
    
    table_detail = pd.DataFrame(dict_col_additional, index=lt)
    
    dict_col_size = {}
    dict_col_size['Source'] = ['battery capacity [kwh]', 'Number of batteries', 'Power [kW]']
    dict_col_size['Sizing'] = [dict_max_st, dict_e_usable, dict_battery_power]
    table_size = pd.DataFrame(dict_col_size)
    
    
    path = 'D:\Subjects\Year 2\Thesis\\v11\\V8_degradation_cost\\result.xlsx'
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        table_h.to_excel(writer, sheet_name ='Hourly')
        table_size.to_excel(writer, sheet_name='Size')
        table_detail.to_excel(writer, sheet_name='Details')
        
    return print('End of postprocessing')