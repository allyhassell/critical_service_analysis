'''Import'''
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from datetime import datetime
import scikit_posthocs as sp
from openpyxl import load_workbook
import numpy as np

'''Defines classes  Census, Boundry, CriticalServices, DataFrames and StatisticalAnalysis'''

class Census:
    '''Census object and methods:
    - Dataframe of census info from opening file
    - Cleanses the data 
    - Adds a column containing the coodinates of the centroid for each land-patch/row'''
    
    TO_REPLACE = ['C', -999, -998, '0', '..', 'Mainland']
    
    def __init__(self, filename):
        '''Creates a new census object'''
        self.filename = filename
    
    def census_df(self):
        '''Opens file and clenses data'''
        census = gpd.read_file(self.filename)
        for replace in self.TO_REPLACE:
            census = census.replace(replace, 0)
        return census
    
    def centroid(self):
        '''Dataframe centroids'''
        dataframe = self.census_df()
        dataframe["centroid"] = dataframe["geometry"].centroid
        return dataframe
    
class Boundry:
    '''Boundries object and methods
    - Opens boundaryfile and creates dataframe 
      Locates specific row which matches specified location
      Clips previous census dataframe to boundary
    '''
    
    def __init__(self, filename, location, census_df):
        '''Creates boundry object'''
        self.filename = filename
        self.location = location
        self.census_df = census_df
        
    def boundry_fig(self):
        '''Boundry dataframe opens file, finds location and clips census to that boundary'''
        boundries = gpd.read_file(self.filename)
        boundry = boundries.loc[boundries['UR2022_V_1'] == self.location]
        return boundry
    
    def boundry(self):
        '''Clips census data to chosen boundary '''
        boundry = self.boundry_fig()
        boundry = boundry.iloc[0, 8]
        boundry_census = gpd.clip(self.census_df, boundry)
        return boundry_census
        
class CriticalServices:
    '''Critical services object and methods
    - Opens file and create df and sets it to the same coodinates as census file
    - '''
    
    def __init__(self, filename, boundry, code):
        '''Initialising critical services class'''
        self.filename = filename
        self.boundry = boundry
        self.code = code
        
    def critical_services_df(self):
        '''Opens and clenses critical service df'''
        cs_df = gpd.read_file(self.filename)
        cs_df = cs_df.to_crs('epsg:2193')
        return cs_df
    
    def critical_boundry_df(self):
        '''Clips critical services to boundry'''
        critical_boundry = gpd.clip(self.critical_services_df(), self.boundry)
        return critical_boundry
    
    def critical_df(self):
        '''Specifies a critical service'''
        critical_boundry_df = self.critical_boundry_df()
        critical_df = critical_boundry_df.loc[critical_boundry_df['code'] == self.code]
        return critical_df
    
    def centroid(self):
        '''Centroid of critical service'''
        dataframe = self.critical_df()
        dataframe["centroid"] = dataframe["geometry"].centroid
        return dataframe


class DataFrames:
    '''Objects and method to determine the minimum distance'''
    
    CODES = [2110, 2101, 2111, 2120, 2204, 2002, 2001, 2082, 2501, 2601, 2901, 2007]
    KEYS = ['hospitals', 'pharmacys', 'clinics', 'doctors', 'parks', 'fire stations', 'police stations', 'schools', 'supermarkets', 'banks', 'toilets', 'libraries']
    LOCATION = 'Christchurch'
    DROPPING = [['hospitals', 'Christchurch Public Hospital']]
    HEALTH_CLEANSE = [['hospitals', 'clinics', 'Christchurch Hospital', False], ['clinics', 'doctors', 'Medical Centre|Health Care', True]]
    
    def __init__(self, census_filename, boundry_filename, critical_filename, save_to):
        '''Initialising for minimum distance'''
        self.census_filename = census_filename
        self.boundry_filename = boundry_filename
        self.critical_filename = critical_filename
        self.save_to = save_to
        
    def location_df(self):
        '''Creates census dataframe'''
        census = Census(self.census_filename)
        census_df = census.centroid()
        location = Boundry(self.boundry_filename, self.LOCATION, census_df)
        location_df = location.boundry()
        return location_df
    
    def critical_dict_df(self):
        location_df = self.location_df()
        critical_dict_df = {}
        for i in range(0, len(self.KEYS)):
            key = self.KEYS[i]
            code = self.CODES[i]
            critical_service = CriticalServices(self.critical_filename, location_df, code)
            df = critical_service.centroid()
            df.drop(df.index[df['name'] == 'None'], inplace = True)
            critical_dict_df[key] = df
        return critical_dict_df
    
    def drop_name(self):
        '''Drop a geopandas row using regexp'''
        dict_df = self.critical_dict_df()
        for drop in self.DROPPING:
            df = dict_df[drop[0]]
            df.drop(df.index[df['name'] == drop[1]], inplace = True)
        return dict_df
    
    def health_data_clense(self):
        '''Cleanses the health dataframes'''
        critical_dict_df = self.drop_name()
        for cleansing in self.HEALTH_CLEANSE:
            df1 = critical_dict_df[cleansing[0]]
            df2 = critical_dict_df[cleansing[1]]
            regexp = cleansing[2]
            boolean = cleansing[3]
            rows = df1[df1.name.str.contains(regexp, regex= True, na=False)]
            df2 = df2.append(rows)
            df1.drop(rows.index, inplace=True)
        return critical_dict_df
    
    def min_distance(self):
        '''Calculates minimum distance'''
        critical_dict_df = self.health_data_clense()
        location_df = self.location_df()
        for key in self.KEYS:
            critical_df = critical_dict_df[key]
            location_df[key[:-1]] = location_df.centroid.apply(lambda x: critical_df.centroid.distance(x).min())
        return location_df
    
    def min_distance_excel(self):
        min_distance = self.min_distance()
        min_distance.to_excel(self.save_to, index = False)
        return min_distance
    
class StatisticalAnalysis():
    '''Objects and method for the statistical analysis'''
    
    KEYS = ['hospitals', 'pharmacys', 'clinics', 'doctors', 'parks', 'fire stations', 'police stations', 'schools', 'supermarkets', 'banks', 'toilets', 'libraries']
    
    def __init__(self, filename, attributes, attribute_names, saved_filename_means, saved_filename_posthoc, overall_attribute):
        '''Initialising parameters for the statistical analysis'''
        self.filename = filename
        self.attributes = attributes 
        self.attribute_names = attribute_names
        self.saved_filename_means = saved_filename_means
        self.saved_filename_posthoc = saved_filename_posthoc
        self.overall_attribute = overall_attribute
        
    def open_file(self):
        '''Opens file'''''
        df = pd.read_excel(self.filename)
        return df
        
    def averages_dict(self):
        'Creates data from excel spreadsheet prev opened'
        dataframe = self.open_file()
        averages_dict = {}
        averages = []
        for key in self.KEYS:
            averages_dict = {}
            for attribute in self.attributes:
                dataframe[attribute + '_distance'] = dataframe[attribute] * dataframe[key[:-1]]
                average = (dataframe[attribute + '_distance'].sum(axis=0)) / dataframe[attribute].sum(axis=0)
                averages_dict[attribute] = average
            averages.append(averages_dict)
        return averages
        
    def means(self):
        '''Empty dataframe ready to be filled'''
        data = self.averages_dict()
        df = pd.DataFrame(data, index=self.KEYS)
        df.columns = self.attribute_names
        return df
    
    def means_df(self):
        '''Saves the dataframe as an excel spreadsheet'''
        df = self.means()
        df.columns = self.attribute_names
        df.to_excel(self.saved_filename_means, index=False)
        
    def nump_dict(self):
        '''Numpy lists of data'''
        df = self.open_file()
        data_list = []
        nump_dict = {}
        for key in self.KEYS:
            key_list = []
            for attribute in self.attributes:
                attribute_list = []
                for index, row in df.iterrows():
                    num = row[attribute]
                    value = row[key[:-1]]
                    attribute_list += num * [value]
                key_list.append(attribute_list)
            nump_list = np.array(key_list)
            nump_dict[key] = nump_list 
        return nump_dict
            
    def df_list(self):
        '''Posthoc analysis dictionary'''
        nump_dict = self.nump_dict()
        df_list = []
        for key in self.KEYS:
            posthoc_df = sp.posthoc_ttest(nump_dict[key])
            posthoc_df.columns = self.attribute_names
            posthoc_df.columns.name = key
            posthoc_df.set_index(self.attribute_names)
            posthoc_df[key] = self.attribute_names
            posthoc_df = posthoc_df.set_index(key)
            df_list.append(posthoc_df)
        return df_list
    
    def posthoc_save(self):
        df_list = self.df_list()
        filename = self.saved_filename_posthoc
        writer = pd.ExcelWriter(filename, engine='xlsxwriter')   
        row = 0
        for dataframe in df_list:
            dataframe.to_excel(writer, sheet_name=self.overall_attribute, startrow=row , startcol=0)
            row = row + len(dataframe.index) + 2
        writer.save()
    
    def boxplot_save(self):
        '''Create and save a boxplot'''
        nump_dict = self.nump_dict()
        for key in self.KEYS:
            data = nump_dict[key]
            flierprops = dict(marker='.', markerfacecolor='gainsboro', markersize=2, linestyle='none')
            plt.xlabel(self.overall_attribute.title())
            plt.ylabel('Minimum distance (m)')
            plt.boxplot(data, flierprops=flierprops, labels=self.attribute_names)
            plt.savefig(f'saved_files/{self.overall_attribute}/boxplot_{key}.png')
            plt.show()
            
    def stat_analysis(self):
        '''Comboned both stat analysis saving functions'''
        posthoc = self.posthoc_save()
        boxplot = self.boxplot_save()
        means = self.means_df()

'''Census, Boundry and DataFrames classes create master spreadsheet of minimum distances to critical services in relation to demographical information'''

def chch_part1_df():
    '''Create chch minimum distance to services census part 1 dataframe'''
    
    '''Parameters'''
    census_filename = 'data/census_part1/2018-census-individual-part-1-total-new-zealand-by-statistic.shp'
    critical_services_filename = 'data/points_of_interest/gis_osm_pois_a_free_1.shp'
    boundry_filename = 'data/city_boundry/urban-rural-2022-clipped-generalised.shp'
    save_to = r'saved_files/part1_min_distance_df.xlsx'
    
    '''Classes'''
    chch = DataFrames(census_filename, boundry_filename, critical_services_filename, save_to)
    chch_min_df = chch.min_distance_excel()
    return chch_min_df


def chch_part2_df():
    '''Create chch minimum distance to services census part 2 dataframe'''
    
    '''Parameters'''
    census_filename = 'data/census_part2/2018-census-individual-part-2-total-new-zealand-by-statistic.shp'
    critical_services_filename = 'data/points_of_interest/gis_osm_pois_a_free_1.shp'
    boundry_filename = 'data/city_boundry/urban-rural-2022-clipped-generalised.shp'
    save_to = r'saved_files/part2_min_distance_df.xlsx'
    
    '''Classes'''
    chch = DataFrames(census_filename, boundry_filename, critical_services_filename, save_to)
    chch_min_df = chch.min_distance_excel()
    return chch_min_df

'''StatisticalAnalysis class analyses master sheet to determine if there is any correlation between demographics and distance traveled'''

def chch_ethnicity_df():
    '''Christchurch ethnicity minimum distance dataframe'''
    
    '''Parameters'''
    overall_attribute = 'ethnicity'
    codes = ['C18_Ethnic', 'C18_Ethn_1', 'C18_Ethn_2', 'C18_Ethn_3', 'C18_Ethn_4', 'C18_Ethn_5']
    names = ['European', 'Maori', 'Pacific Peoples', 'Asian', 'MELA', 'Other']
    filename = 'saved_files/part1_min_distance_df.xlsx'
    saved_filename_means = 'saved_files/ethnicity/means.xlsx'
    saved_filename_posthoc = 'saved_files/ethnicity/posthoc.xlsx'
    
    '''Classes'''
    chch_df = StatisticalAnalysis(filename, codes, names, saved_filename_means, saved_filename_posthoc, overall_attribute)
    chch_df = chch_df.stat_analysis()
    return chch_df

def chch_age_df():
    '''Christchurch age minimum distance '''
    
    '''Parameters'''
    overall_attribute = 'age'
    codes = ['C18_Age5ye', 'C18_Age5_1', 'C18_Age5_2', 'C18_Age5_3', 'C18_Age5_4', 'C18_Age5_5', 'C18_Age5_6', 'C18_Age5_7', 'C18_Age5_8', 'C18_Age5_9', 'C18_Age510', 'C18_Age511', 'C18_Age512', 'C18_Age513', 'C18_Age514', 'C18_Age515', 'C18_Age516', 'C18_Age517']
    names = ['1 to 4', '5 to 9', '10 to 14', '15 to 19', '20 to 24', '25 to 29', '30 to 34', '35 to 39', '40 to 44', '45 to 49', '50 to 54', '55 to 59', '60 to 64', '65 to 69', '70 to 74', '75 to 79', '80 to 84', '85 and above']
    filename = 'saved_files/part1_min_distance_df.xlsx'
    saved_filename_means = 'saved_files/age/means.xlsx'
    saved_filename_posthoc = 'saved_files/age/posthoc.xlsx'
    
    '''Classes'''
    chch_df = StatisticalAnalysis(filename, codes, names, saved_filename_means, saved_filename_posthoc, overall_attribute)
    chch_df = chch_df.stat_analysis()
    return chch_df

def chch_income_df():
    '''Christchurch home ownership minimum distance dataframe'''
    
    '''Parameters'''
    overall_attribute = 'income'
    codes = ['C18_Groupe', 'C18_Grou_1', 'C18_Grou_2',  'C18_Grou_3', 'C18_Grou_4', 'C18_Grou_5', 'C18_Grou_6']
    names = ['Less than 5k', '5k to 10k', '10k to 20k', '20k to 30k', '30k to 50k', '50k to 70k', 'Over 70k']
    filename = 'saved_files/part2_min_distance_df.xlsx'
    saved_filename_means = 'saved_files/income/means.xlsx'
    saved_filename_posthoc = 'saved_files/income/posthoc.xlsx'
    
    '''Classes'''
    chch_df = StatisticalAnalysis(filename, codes, names, saved_filename_means, saved_filename_posthoc, overall_attribute)
    chch_df = chch_df.stat_analysis()
    return chch_df

def main():
    '''Census and statistical analysis'''
    
    '''Christchurch minimum distance dataframe part 1 and 2'''
    chch_part1 = chch_part1_df()
    chch_part2 = chch_part2_df()
    '''Analyse ethnicity, age and income'''
    chch_ethnicity_df()
    chch_age_df()
    chch_income_df()
    
main()