import pandas as pd


path = 'D:\Subjects\Year 2\Thesis\Pyomo\Data\cag.xlsx' # High load
# path = 'D:\Subjects\Year 2\Thesis\Pyomo\Data\Low_load\cag.xlsx' #Low load
import_demand = pd.read_excel(path, sheet_name='Load', index_col=0)
import_pv = pd.read_excel(path, sheet_name='PV', index_col=0)



### Lifetime Year ###

l_proj = 20*365  # Inverter life time
calendar_life =15*365 # Calendar lifetime for battery
cyclic_life = 10000 # Number of cycles for the battery
replacement = 0.6 # Replacement percentage 60%

### Electricity cost ###
tou = 0.40 # cost of electricity from grid
fit = 0.36 # cost for selling it back to the grid

## Battery:

batt_eff = 0.98     #battery efficiency
self_discharge = 0.0002/96 # self discharge for every 15 mins
capex_battery = 395   #euro/kwh
inverter_cost = 155   #euro/kwh
fixed_cost = 1723     #euros

## Connection:
contract_power = 1000 #kVA  #Transformer capacity  


lt = list(range(0, len(import_demand.index))) # Time index


def dict_demand(importa): # Load and PV generation with each time slot
    dict_Forecast = {t: importa.iloc[t, 1] for t in lt}
    return dict_Forecast

def get_import(x):  # To get the load and PV generation data
    if x == 'Demand':
        return import_demand
    elif x == 'PV':
        return import_pv
    else:
        return  #add an exception statement

def get_t():   # To get the time index
    return lt

def get_prj(x):
    if x == 'project':
        return l_proj
    elif x == 'battery':
        return l_proj

def info_battery(x):
    if x == 'capex':
        return capex_battery
    elif x == 'inverter_cost':
        return inverter_cost
    elif x == 'replacement':
        return replacement
    elif x == 'calendar':
        return calendar_life
    elif x == 'cycle':
        return cyclic_life
    elif x == 'SD':
        return self_discharge
    elif x == 'fix':
        return fixed_cost

def tariff(x):
    if x == 'tou':
        return tou
    elif x == 'fit':
        return fit
    
def info_connection(x):
    if x == 'contract':
        print(f'The Grid connection capacity:{contract_power}')
        return contract_power



#### Test output

# print(dict_demand(get_import('Demand')))




