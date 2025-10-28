
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QProcess, QProcessEnvironment
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import *


import random
import threading

import xml.etree.ElementTree as ET
import sys
import os
from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsApplication, QgsRectangle, QgsCoordinateTransform

class Importer:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.isRun=None
        self.folder_path=os.path.expanduser('~')
        
    def initGui(self):
        icon = QIcon(os.path.join(self.plugin_dir,"icon.png"))
        action = QAction(icon, "UA XML Importer ( ◔ ౪◔)⊃━☆ﾟ.*・",self.iface.mainWindow())
        action.triggered.connect(self.run)
        action.setEnabled(True)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)
    def unload(self):
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
    def zoom_to_layers(self,layers):
        canvas = self.iface.mapCanvas()
        extent = QgsRectangle()
        transform_context = QgsProject.instance().transformContext()

        for layer in layers:
            if layer.crs() != canvas.mapSettings().destinationCrs():
                transform = QgsCoordinateTransform(layer.crs(), canvas.mapSettings().destinationCrs(), QgsProject.instance())
                bottom_left = QgsPointXY(layer.extent().xMinimum(), layer.extent().yMinimum())
                top_right = QgsPointXY(layer.extent().xMaximum(), layer.extent().yMaximum())
                transformed_bottom_left = transform.transform(bottom_left)
                transformed_top_right = transform.transform(top_right)
                layer_extent = QgsRectangle(transformed_bottom_left, transformed_top_right)
            else:
                layer_extent = layer.extent()

            extent.combineExtentWith(layer_extent)

        canvas.setExtent(extent)
        canvas.refresh()
    def run(self):
        finished_arr=[]
        err_dict={'parc_inv':[],'rest_inv':[],'other_inv':[],'parc_err':[],'rest_err':[],'other_err':[]}
        crs_layers={}
        pathArr=[]
        def get_crs(root):
            epsg={
                'SC63X/1':'7825',
                'SC63X/2':'7826',
                'SC63X/3':'7827',
                'SC63X/4':'7828',
                'SC63X/5':'7829',
                'SC63X/6':'7830',
                'SC63X/7':'7831',
                'Local/01': '9831',
                'Local/05': '9832',
                'Local/07': '9833',
                'Local/12': '9834',
                'Local/14': '9835',
                'Local/18': '9836',
                'Local/21': '9837',
                'Local/23': '9838',
                'Local/35': '9840',
                'Local/44': '9841',
                'Local/46': '9851',
                'Local/48': '9852',
                'Local/51': '9853',
                'Local/53': '9854',
                'Local/56': '9855',
                'Local/59': '9856',
                'Local/61': '9857',
                'Local/63': '9858',
                'Local/65': '9859',
                'Local/68': '9860',
                'Local/71': '9861',
                'Local/73': '9862',
                'Local/74': '9863',
                'Local/85': '9865',
                'Local/32': '9821',
                'Local/26': '9839',
                'Local/80': '9864',
                'UCS-2000/7':'6381',
                'UCS-2000/8':'6382',
                'UCS-2000/9':'6383',
                'UCS-2000/10':'6384',
                'UCS-2000/11':'6385',
                'UCS-2000/12':'6386',
                'UCS-2000/13':'6387',
            }
            crs_type=root.find("./InfoPart/MetricInfo/CoordinateSystem/")            
            if crs_type!=None:
                crs_type=crs_type.tag
            else:
                return ['','None']
            
            if crs_type=="SC63":
                crs_type=crs_type+root.find("./InfoPart/MetricInfo/CoordinateSystem/*/").tag
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="USC2000":
                crs_zone=root.find("./InfoPart/MetricInfo/PointInfo/Point/Y").text[0]
                crs_comb=crs_type+'/'+crs_zone
            elif crs_type=="Local":
                try:
                    crs_zone=root.find("./InfoPart/MetricInfo/CoordinateSystem/").text[-2:]
                except (AttributeError,TypeError):
                    crs_zone='undefined'
                crs_comb='Local/'+crs_zone
            else:
                crs_comb=root.find("./InfoPart/MetricInfo/CoordinateSystem/").tag
            if crs_comb in epsg:
                # print(epsg[crs_comb])
                return ['crs=epsg:'+epsg[crs_comb]+'&',crs_comb]
            else:
                # print("Ск не розпізнана")
                return ['',crs_comb]
        def get_geometry(xml_path):#об'єкт xmlPath до /externals
            if xml_path==None: return None
            res_geom= QgsGeometry.fromWkt('GEOMETRYCOLLECTION()')
            geom_arr=[]
            for element in xml_path:
                ParcExtBound=[]            
                for child in element.findall("./Boundary/Lines/Line"):                    
                    fp=child.find('./FP')
                    tp=child.find('./TP')
                    if fp!=None: fp=int(fp.text)
                    if tp!=None: tp=int(tp.text)
                    if fp in points and tp in points:
                        ParcExtBound=ParcExtBound+[points[fp],points[tp]]
                    else:
                        ParcExtBound=ParcExtBound+lines[int(child.find("./ULID").text)]                
                geom=QgsGeometry().fromPolygonXY([ParcExtBound]) 
                
                for child in element.findall("./Internals/Boundary"):
                    ParcInttBound=[]
                    for shape in child.findall("./Lines/Line"):
                        fp=shape.find('./FP')                    
                        tp=shape.find('./TP')                    
                        if fp!=None: fp=int(fp.text)
                        if tp!=None: tp=int(tp.text)
                        if fp in points and tp in points:
                            ParcInttBound=ParcInttBound+[points[fp],points[tp]]
                        else:
                            ParcInttBound=ParcInttBound+lines[int(shape.find("./ULID").text)]
                    geom=geom.difference(QgsGeometry().fromPolygonXY([ParcInttBound]))
                    geom_arr.append(geom)
                res_geom=res_geom.combine(geom.makeValid())   
            return res_geom
        def convert_string_to_float(string_with_comma):            
            string_with_dot = string_with_comma.replace(',', '.')
            try:
                result = float(string_with_dot)
                return result
            except ValueError:                
                print(f"Помилка: '{string_with_dot}' невірне число.")
                return None
        pathArr=QFileDialog.getOpenFileNames(None,"Виберіть XML файл(файли) для імпорту", self.folder_path, "Кадастровий XML (*.xml)")[0]
        if pathArr==[]:
            print('Нічого не вибрано!')
            return
        print(str(len(pathArr))+' файлів до обробки:')
        print('\t'+str(pathArr))
        self.folder_path=os.path.dirname(pathArr[0])
        
        window = QProgressDialog(self.iface.mainWindow())
        window.setWindowTitle("Обробляю...")            
        bar = QProgressBar(window)
        bar.setTextVisible(True)
        bar.setValue(0)
        bar.setMaximum(len(pathArr))
        window.setBar(bar)
        window.setMinimumWidth(300)
        window.show()
        

        for path in pathArr:
            if path!='':
                print('Обробляю '+os.path.basename(path))
                _print=lambda t: print('\t'+str(t))
                tree = ET.parse(path)
                root = tree.getroot()
                crs=get_crs(root)[0]                
                _print('З тегу СК прочитано:'+get_crs(root)[1])
                if crs: _print(crs)
                if crs=='': crs=get_crs(root)[1] #якшо не визначило epsg тоді вписуємо шо воно витягло з XML
                points={}#словарь з списком точок 'UIDP': [x,y]
                for child in root.findall("./InfoPart/MetricInfo/PointInfo/Point"):
                    points[int(child.find("./UIDP").text)]=QgsPointXY(convert_string_to_float(child.find("./Y").text),convert_string_to_float(child.find("./X").text))
                _print(f"Знайдено {len(points)} точок")
                linesC={}#словарь з списком ліній 'ULID':[UIDP, UIDP, UIDP...]
                for child in root.findall("./InfoPart/MetricInfo/Polyline/PL"):
                    linesC[int(child.find("./ULID").text)]=[int(i.text) for i in child.findall("./Points/P")]
                _print(f"Знайдено {len(linesC)} ліній")
                lines={}#словарь з списком ліній 'ULID':[QgsPointXY, QgsPointXY, QgsPointXY...]
                for linenum in linesC:
                    lines[linenum]=[points[i] for i in linesC[linenum]]

#Ділянки------------------------------------------------
                _print('Перевіряю ділянки...')
                for element in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo"):                    
                    try:
                        purpose=element.find("./CategoryPurposeInfo/Purpose").text
                    except AttributeError:
                        purpose='*не роспізнано*'
                        _print("\t\tPurpose не знайдено")
                    try:
                        use=element.find("./CategoryPurposeInfo/Use").text
                    except AttributeError:
                        use='*не роспізнано*'
                        _print("\t\tUse не знайдено")
                    try:
                        area=element.find("./ParcelMetricInfo/Area/Size").text
                    except AttributeError:
                        area='*не роспізнано*'
                        _print("\t\tПлощу не знайдено")
                    try:
                        area_unit=element.find("./ParcelMetricInfo/Area/MeasurementUnit").text
                    except AttributeError:
                        area_unit='?'
                        _print("\t\tОдиниці площі не знайдено")
                    feature = QgsFeature()
                    feature.initAttributes(5)
                    feature.setAttribute(0,os.path.basename(path))                    
                    feature.setAttribute(1,use) 
                    feature.setAttribute(2,purpose)                    
                    try:
                        a={"100":"Приватна власність","200":"Комунальна власність", "300":"Державна власність"}
                        if element.find("./OwnershipInfo/Code").text in a:
                            feature.setAttribute(3,a[element.find("./OwnershipInfo/Code").text])
                        else:
                            feature.setAttribute(3,element.find("./OwnershipInfo/Code").text)
                    except AttributeError:
                        feature.setAttribute(3,'*не роспізнано*')
                        _print("\t\tOwnership не знайдено")
                    feature.setAttribute(4,area+' '+area_unit)
                    
                    geom=get_geometry(element.findall("./ParcelMetricInfo/Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('Геометрія ділянки пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['parc_inv']: err_dict['parc_inv'].append(os.path.basename(path))
                            _print('Геометрія ділянки не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                        
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Parcels' in crs_layers[crs]: crs_layers[crs]['Parcels']=[]
                        crs_layers[crs]['Parcels'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['parc_err']: err_dict['parc_err'].append(os.path.basename(path))
                        _print('Не можу знайти геометрію ділянки. Ділянка не буде додана.')
            
#restrictions------------------------------------------------
                _print('Перевіряю обмеження...')
                for restriction in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/Restrictions/RestrictionInfo"): 
                    try:
                        rest_code=restriction.find('./RestrictionCode').text
                    except AttributeError:
                        rest_code='*код не роспізнано*'                        
                    try:
                        rest_name=restriction.find('./RestrictionName').text
                    except AttributeError:
                        rest_name='*назву не роспізнано*'                        
                    _print(f"\tРозглядаємо обмеження {rest_code} {rest_name}...")
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,rest_code)
                    feature.setAttribute(2,rest_name)
                    geom=get_geometry(restriction.findall("./Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('\t\tГеометрія Обмеження пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['rest_inv']: err_dict['rest_inv'].append(os.path.basename(path))
                            _print('\t\tГеометрія Обмеження не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                            
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Restrictions' in crs_layers[crs]: crs_layers[crs]['Restrictions']=[]
                        crs_layers[crs]['Restrictions'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['rest_err']: err_dict['rest_err'].append(os.path.basename(path))
                        _print('\t\tНе можу знайти геометрію обмеження. Обмеження не буде додано.')
# угіддя ------------------------------------------------
                    land_use_types = {
                    '001.00': 'Рілля',
                    '001.01': 'Рілля',
                    '001.02': 'Перелоги',
                    '001.03': 'Парники, оранжереї, теплиці',
                    '002.00': 'Рослинний покрив земель і ґрунти',
                    '002.01': 'Сіножаті',
                    '002.02': 'Пасовища',
                    '002.03': 'Багаторічні насадження',
                    '003.00': 'Землі без рослинного покриву або з незначним рослинним покривом, абоав’янистим рослинним                  покривом природного походження',
                    '003.01': "Кам'янисті місця",
                    '003.02': 'Піски',
                    '003.03': 'Болота',
                    '003.04': 'Солончаки',
                    '003.05': 'Яри',
                    '003.06': 'Степи',
                    '003.07': 'Луки',
                    '004.00': 'Чагарникова рослинність природного походження',
                    '005.00': 'Ліси та інші лісовкриті землі',
                    '005.01': 'Земельні лісові ділянки, вкриті лісовою рослинністю',
                    '005.02': 'Земельні лісові ділянки, не вкриті лісовою рослинністю',
                    '005.03': 'Лісові насадження лінійного типу',
                    '005.04': 'Інші лісовкриті площі',
                    '005.05': 'Самозалісені землі',
                    '006.00': 'Води',
                    '006.01': 'Природні водотоки (річки та струмки)',
                    '006.02': 'Штучні водотоки (канали, колектори, канави)',
                    '006.03': 'Озера, прибережні замкнуті водойми, лимани',
                    '006.04': 'Ставки',
                    '006.05': 'Штучні водосховища',
                    '007.00': 'Землі під житловою забудовою',
                    '007.01': 'Малоповерхова забудова',
                    '007.02': 'Багатоповерхова забудова',
                    '008.00': 'Землі під громадською забудовою',
                    '008.01': 'Землі під громадськими спорудами, які мають історико-архітектурнуцінність',
                    '008.02': 'Вулиці та бульвари, набережні, площі',
                    '008.03': 'Землі під соціально-культурними об’єктами',
                    '009.00': 'Землі, які використовуються для транспорту',
                    '009.01': 'Землі під залізницями',
                    '009.02': 'Землі під дорогами',
                    '009.03': 'Землі під будівлями та спорудами транспорту',
                    '010.00': 'Землі технічної інфраструктури',
                    '011.00': 'Землі під промисловою забудовою',
                    '011.01': 'Землі під будівлями промислових підприємств',
                    '011.02': 'Землі під відкритими розробками, шахтами, кар’єрами',
                    '011.03': 'Забруднені промисловими та іншими відходами землі',
                    '012.00': 'Землі поточного будівництва',
                    '013.00': 'Землі під господарськими будівлями і дворами',
                    '014.00': 'Землі для відпочинку та оздоровлення',
                    '015.00': 'Землі спеціального призначення',
                    '015.01': 'Військові бази, фортеці',
                    '015.02': 'Кладовища, крематорії, меморіали',
                    '015.03': 'Меліоративне освоєння і відновлення родючості ґрунтів',
                # старі коди
                    '03': 'Сільськогосподарські землі (6-зем)',
                    '04': 'сільськогосподарські угіддя (6-зем)',
                    '05': 'рілля (6-зем)',
                    '06': 'перелоги (6-зем)',
                    '07': 'багаторічні насадження (6-зем)',
                    '08': 'садів (багаторічні насадження) (6-зем)',
                    '09': 'виноградників (багаторічні насадження) (6-зем)',
                    '10': 'інших багаторічних насаджень (багаторічні насадження) (6-зем)',
                    '11': 'сіножаті (6-зем)',
                    '12': 'пасовища (6-зем)',
                    '13': 'з усіх пасовищ гірські (пасовища) (6-зем)',
                    '14': 'під господарськими будівлями і дворами (6-зем)',
                    '15': 'під господарськими шляхами і прогонами (6-зем)',
                    '16': 'землі меліоративного будівництва та відновлення родючості (6-зем)',
                    '17': 'землі тимчасової консервації (6-зем)',
                    '18': 'забруднені сільськогосподарські угіддя, що не використовуються (6-зем)',
                    '19': 'техногенно забруднені, включаючи радіонуклідне (6-зем)',
                    '20': 'інші сільськогосподарські землі (6-зем)',

                    '21': 'Ліси та інші лісовкриті площі (6-зем)',
                    '22': 'лісові землі (Ліси та інші лісовкриті площі) (6-зем)',
                    '23': 'вкриті лісовою (деревною та чагарниковою) рослинністю (лісові землі) (6-зем)',
                    '24': 'полезахисні лісосмуги (вкриті лісовою рослинністю) (6-зем)',
                    '25': 'інші захисні насадження (вкриті лісовою рослинністю) (6-зем)',
                    '26': 'не вкриті лісовою рослинністю (лісові землі) (6-зем)',
                    '27': 'інші лісові землі (лісові землі) (6-зем)',
                    '28': 'чагарники (Ліси та інші лісовкриті площі) (6-зем)',
                    '29': 'група I (Ліси та інші лісовкриті площі) (6-зем)',
                    '30': 'група II (Ліси та інші лісовкриті площі) (6-зем)',
                    '31': 'усі лісовкриті площі (Ліси та інші лісовкриті площі) (6-зем)',
                    '32': 'для захисної, природоохоронної та біологічної мети (Ліси та інші лісовкриті площі) (6-зем)',
                    '33': 'для відпочинку (Ліси та інші лісовкриті площі) (6-зем)',

                    '34': 'Забудовані землі (6-зем)',
                    '35': 'житлова забудова одно- та двоповерхова (6-зем)',
                    '35.1': 'капітальна (житлова забудова одно- та двоповерхова) (6-зем)',
                    '35.2': 'тимчасова (житлова забудова одно- та двоповерхова) (6-зем)',
                    '35.3': 'прибудинкова територія (житлова забудова одно- та двоповерхова) (6-зем)',

                    '36': 'житлова забудова триповерхова і вище (6-зем)',
                    '36.1': 'капітальна (житлова забудова триповерхова і вище) (6-зем)',
                    '36.2': 'тимчасова (житлова забудова триповерхова і вище) (6-зем)',
                    '36.3': 'під спортивними та дитячими майданчиками (житлова забудова триповерхова і вище) (6-зем)',
                    '36.4': 'під проїздами, проходами та площадками (житлова забудова триповерхова і вище) (6-зем)',
                    '36.5': 'прибудинкова територія (житлова забудова триповерхова і вище) (6-зем)',

                    '37': 'землі промисловості (6-зем)',
                    '37.1': 'капітальна одноповерхова (землі промисловості) (6-зем)',
                    '37.2': 'капітальна трьох і більше поверхова (землі промисловості) (6-зем)',
                    '37.3': 'тимчасова (землі промисловості) (6-зем)',
                    '37.4': 'під спорудами (землі промисловості) (6-зем)',
                    '37.5': 'під проїздами, проходами та площадками (землі промисловості) (6-зем)',
                    '37.6': 'під зеленими насадженнями (землі промисловості) (6-зем)',
                    '37.7': 'під спортивними та дитячими майданчиками (землі промисловості) (6-зем)',
                    '37.8': 'інші (землі промисловості) (6-зем)',

                    '38': 'землі під відкритими розробками, кар’єрами, шахтами (6-зем)',
                    '39': 'під торфорозробками, які експлуатують (землі під відкритими розробками) (6-зем)',
                    '40': 'відкриті розробки та кар’єри, шахти, які експлуатують (землі під відкритими розробками) (6-зем)',
                    '41': 'інші (відпрацьовані, закриті, відвали, терикони) (землі під відкритими розробками) (6-зем)',

                    '42': 'землі, які використовуються в комерційних цілях (6-зем)',
                    '42.1': 'капітальна одноповерхова (комерційні землі) (6-зем)',
                    '42.2': 'капітальна трьох і більше поверхова (комерційні землі) (6-зем)',
                    '42.3': 'тимчасова (комерційні землі) (6-зем)',
                    '42.4': 'під спорудами (комерційні землі) (6-зем)',
                    '42.5': 'під проїздами, проходами та площадками (комерційні землі) (6-зем)',
                    '42.6': 'під зеленими насадженнями (комерційні землі) (6-зем)',
                    '42.7': 'під спортивними та дитячими майданчиками (комерційні землі) (6-зем)',
                    '42.8': 'інші (комерційні землі) (6-зем)',

                    '43': 'землі громадського призначення (6-зем)',
                    '43.1': 'капітальна одноповерхова (землі громадського призначення) (6-зем)',
                    '43.2': 'капітальна трьох і більше поверхова (землі громадського призначення) (6-зем)',
                    '43.3': 'тимчасова (землі громадського призначення) (6-зем)',
                    '43.4': 'під спорудами (землі громадського призначення) (6-зем)',
                    '43.5': 'під проїздами, проходами та площадками (землі громадського призначення) (6-зем)',
                    '43.6': 'під зеленими насадженнями (землі громадського призначення) (6-зем)',
                    '43.7': 'під спортивними та дитячими майданчиками (землі громадського призначення) (6-зем)',
                    '43.8': 'інші (землі громадського призначення) (6-зем)',

                    '44': 'землі змішаного використання (6-зем)',
                    '44.1': 'капітальна одноповерхова (землі змішаного використання) (6-зем)',
                    '44.2': 'капітальна трьох і більше поверхова (землі змішаного використання) (6-зем)',
                    '44.3': 'тимчасова (землі змішаного використання) (6-зем)',
                    '44.4': 'під спорудами (землі змішаного використання) (6-зем)',
                    '44.5': 'під проїздами, проходами та площадками (землі змішаного використання) (6-зем)',
                    '44.6': 'під зеленими насадженнями (землі змішаного використання) (6-зем)',
                    '44.7': 'під спортивними та дитячими майданчиками (землі змішаного використання) (6-зем)',
                    '44.8': 'інші (землі змішаного використання) (6-зем)',

                    '45': 'забудовані землі для транспорту та зв’язку (6-зем)',
                    '46': 'під дорогами (забудовані землі транспорту) (6-зем)',
                    '47': 'під залізницями (забудовані землі транспорту) (6-зем)',
                    '48': 'під аеропортами та відповідними спорудами (забудовані землі транспорту) (6-зем)',
                    '49': 'інші забудовані землі (6-зем)',
                    '49.1': 'капітальна одноповерхова (інші забудовані землі) (6-зем)',
                    '49.2': 'капітальна трьох і більше поверхова (інші забудовані землі) (6-зем)',
                    '49.3': 'тимчасова (інші забудовані землі) (6-зем)',
                    '49.4': 'під спорудами (інші забудовані землі) (6-зем)',
                    '49.5': 'під проїздами, проходами та площадками (інші забудовані землі) (6-зем)',
                    '49.6': 'під зеленими насадженнями (інші забудовані землі) (6-зем)',
                    '49.7': 'під спортивними та дитячими майданчиками (інші забудовані землі) (6-зем)',
                    '49.8': 'інші (інші забудовані землі) (6-зем)',

                    '50': 'технічна інфраструктура (6-зем)',
                    '51': 'для видалення відходів (технічна інфраструктура) (6-зем)',
                    '52': 'для водозабезпечення та очищення стічних вод (технічна інфраструктура) (6-зем)',
                    '53': 'для виробництва та розподілення електроенергії (технічна інфраструктура) (6-зем)',
                    '54': 'інші технічні землі (6-зем)',
                    '54.1': 'капітальна одноповерхова (інші технічні землі) (6-зем)',
                    '54.2': 'капітальна трьох і більше поверхова (інші технічні землі) (6-зем)',
                    '54.3': 'тимчасова (інші технічні землі) (6-зем)',
                    '54.4': 'під спорудами (інші технічні землі) (6-зем)',
                    '54.5': 'під проїздами, проходами та площадками (інші технічні землі) (6-зем)',
                    '54.6': 'під зеленими насадженнями (інші технічні землі) (6-зем)',
                    '54.7': 'інші (інші технічні землі) (6-зем)',

                    '55': 'забудовані землі для відпочинку та відкриті землі (6-зем)',
                    '56': 'зелені насадження загального користування (забудовані землі відпочинку) (6-зем)',
                    '57': 'кемпінги, будинки відпочинку або для проведення відпустки (забудовані землі відпочинку) (6-зем)',
                    '57.1': 'капітальна одноповерхова (кемпінги/будинки відпочинку) (6-зем)',
                    '57.2': 'капітальна трьох і більше поверхова (кемпінги/будинки відпочинку) (6-зем)',
                    '57.3': 'тимчасова (кемпінги/будинки відпочинку) (6-зем)',
                    '57.4': 'під спорудами (кемпінги/будинки відпочинку) (6-зем)',
                    '57.5': 'під проїздами, проходами та площадками (кемпінги/будинки відпочинку) (6-зем)',
                    '57.6': 'під зеленими насадженнями (кемпінги/будинки відпочинку) (6-зем)',
                    '57.7': 'під спортивними та дитячими майданчиками (кемпінги/будинки відпочинку) (6-зем)',
                    '57.8': 'інші (кемпінги/будинки відпочинку) (6-зем)',

                    '58': 'зайняті поточним будівництвом (6-зем)',
                    '59': 'відведені під будівництво (6-зем)',
                    '60': 'під гідротехнічними спорудами (6-зем)',
                    '61': 'вулиць, набережних, площ (6-зем)',
                    '62': 'кладовищ (6-зем)',

                    '63': 'Відкриті заболочені землі (6-зем)',
                    '64': 'верхові (Відкриті заболочені землі) (6-зем)',
                    '65': 'низинні (Відкриті заболочені землі) (6-зем)',

                    '66': 'Сухі відкриті землі з особливим рослинним покривом (6-зем)',
                    '67': 'Відкриті землі без рослинного покриву або з незначним рослинним покривом (6-зем)',
                    '68': 'кам’янисті місця (Відкриті землі без рослинного покриву) (6-зем)',
                    '69': 'піски (включаючи пляжі) (Відкриті землі без рослинного покриву) (6-зем)',
                    '70': 'яри (Відкриті землі без рослинного покриву) (6-зем)',
                    '71': 'інші (Відкриті землі без рослинного покриву) (6-зем)',

                    '72': 'Води (6-зем)',
                    '73': 'природними водотоками (річками та струмками) (Води) (6-зем)',
                    '74': 'штучними водотоками (каналами, колекторами, канавами) (Води) (6-зем)',
                    '75': 'озерами, прибережними замкнутими водоймами, лиманами (Води) (6-зем)',
                    '76': 'ставками (Води) (6-зем)',
                    '77': 'штучними водосховищами (Води) (6-зем)',

                    '78': 'З усіх земель природоохоронного призначення (6-зем)',
                    '79': 'оздоровчого призначення (З усіх земель природоохоронного призначення) (6-зем)',
                    '80': 'рекреаційного призначення (З усіх земель природоохоронного призначення) (6-зем)',
                    '81': 'історико-культурного призначення (З усіх земель природоохоронного призначення) (6-зем)',
                    }
                    _print('Перевіряю угіддя...')
                    for part in root.findall("./InfoPart/CadastralZoneInfo/CadastralQuarters/CadastralQuarterInfo/Parcels/ParcelInfo/LandsParcel/LandParcelInfo"):
                        try:
                            code = part.find('./LandCode').text
                        except AttributeError:
                            code = '*код не розпізнано*'
                            _print("\tКод угіддя не знайдено")

                        land_name = land_use_types.get(code.strip(), '*невідоме угіддя*')

                        try:
                            size = part.find('./MetricInfo/Area/Size').text
                        except AttributeError:
                            size = '*площу не визначено*'
                        try:
                            size = size + ' ' + part.find('./MetricInfo/Area/MeasurementUnit').text
                        except AttributeError:
                            size = size + ' ?'

                        _print(f"\tРозглядаємо угіддя {code} ({land_name})...")

                        feature = QgsFeature()
                        feature.initAttributes(4)
                        feature.setAttribute(0, os.path.basename(path))
                        feature.setAttribute(1, land_name)
                        feature.setAttribute(2, code)
                        feature.setAttribute(3, size)

                        geom = get_geometry(part.findall("./MetricInfo/Externals"))
                        if geom:
                            if geom.isGeosValid():
                                _print('\t\tГеометрія угіддя пройшла валідацію.')
                            else:
                                if os.path.basename(path) not in err_dict['other_inv']:
                                    err_dict['other_inv'].append(os.path.basename(path))
                                _print('\t\tГеометрія угіддя не пройшла валідацію.')

                            feature.setGeometry(geom)
                            if crs not in crs_layers:
                                crs_layers[crs] = {}
                            if 'Others' not in crs_layers[crs]:
                                crs_layers[crs]['Others'] = []
                            crs_layers[crs]['Others'].append(feature)
                            if os.path.basename(path) not in finished_arr:
                                finished_arr.append(os.path.basename(path))
                        else:
                            if os.path.basename(path) not in err_dict['other_err']:
                                err_dict['other_err'].append(os.path.basename(path))
                            _print('\t\tНе можу знайти геометрію Угіддя. Угіддя не буде додано.')


#Тер зони------------------------------------------------
                ter_zones={
                        '001':	'Межі адміністративно-територіальних утворень',
                        '002':	'Зони розподілу земель за їх основним цільовим призначенням',
                        '003':	'Економіко-планувальні зони',
                        '004':	'Зони агровиробничих груп ґрунтів ',
                        '005':	'Зони дії земельних сервітутів',
                        '006':	'Зони дії обмежень використання земель',
                        '007':	'Зони регулювання забудови (функціональні зони)',
                        '008':	'Зони санітарної охорони',
                        '009':	'Охоронні зони',
                        '010':	'Зони особливого режиму використання земель',
                        '011':	'Водоохоронні зони',
                        '012':	'Прибережні захисні смуги',
                        '013':	'Природно-сільськогосподарські зони',
                        '014':	'Еколого-економічні зони',
                        '015':	'Зони протиерозійного районування (зонування)',
                        '016':	'Ключові території екомережі',
                        '017':	'Сполучні території екомережі',
                        '018':	'Буферні зони екомережі',
                        '019':	'Відновлювані території екомережі',
                        '020':	'Інші територіальні зони'
                }
                _print('Перевіряю територіальні зони...')
                for part in root.findall("./InfoPart/TerritorialZoneInfo"): 
                    attr=''
                    try:
                        attr=attr+'Назва: '+part.find('./TerritorialZoneName').text+'; '
                    except AttributeError:
                        pass
                    try:
                        attr=attr+'Тип: '+ter_zones[part.find('./TerritorialZoneNumber/TerritorialZoneCode').text]+'; '
                    except (AttributeError, KeyError):
                        pass
                    try:
                        attr=attr+'Код: '+part.find('./TerritorialZoneNumber/TerritorialZoneShortNumber').text+'; '
                    except AttributeError:
                        pass 
                    feature = QgsFeature()
                    feature.initAttributes(3)
                    feature.setAttribute(0,os.path.basename(path))
                    feature.setAttribute(1,"Територіальна зона")
                    feature.setAttribute(2,attr)
                    geom=get_geometry(part.findall("./Externals"))
                    if geom:
                        if geom.isGeosValid():
                            _print('\t\tГеометрія тер. зони пройшла валідацію.')
                        else:
                            if not os.path.basename(path) in err_dict['other_inv']: err_dict['other_inv'].append(os.path.basename(path))
                            _print('\t\tГеометрія тер. зони не пройшла валідацію, перевірьте правильність імпортованої геометрії.')                            
                        feature.setGeometry(geom)
                        if not crs in crs_layers: crs_layers[crs]={}
                        if not 'Others' in crs_layers[crs]: crs_layers[crs]['Others']=[]
                        crs_layers[crs]['Others'].append(feature)
                        if not os.path.basename(path)in finished_arr: finished_arr.append(os.path.basename(path))
                    else:
                        if not os.path.basename(path) in err_dict['other_err']: err_dict['other_err'].append(os.path.basename(path))
                        _print('\t\tНе можу знайти геометрію тер. зони. Тер. зона не буде додано.')
            bar.setValue(bar.value()+1)

    
#Додавання об'єктів в шари               
        layers_arr=[]
        for crs in crs_layers:
            if crs[0:4]=='crs=':
                epsg=crs                
                group = QgsProject.instance().layerTreeRoot().insertGroup(0,crs[4:-1])
                print(f'\tСтворюю групу шарів {crs[4:-1]}.')
            else:
                epsg='crs=epsg:7827&'
                group = QgsProject.instance().layerTreeRoot().insertGroup(0,crs)
                print(f'\tСтворюю групу шарів {crs}.')
            if 'Restrictions' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=RestrictionCode:string&field=RestrictionName:string', 'XML_restrictions' , "memory")
                for feature in crs_layers[crs]['Restrictions']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\restrictions.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з обмеженнями в групі.')
            else:
                print("\t\tОб'єкти обмежень відсутні.")

            if 'Others' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=LandName:string&field=LandCode:string&field=Area:string', 'XML_landuses' , "memory")
                for feature in crs_layers[crs]['Others']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\others.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з іншою геометрією в групі.')
            else:
                print("\t\tІнші об'єкти відсутні.")
            layer=None


            if 'Parcels' in crs_layers[crs]:
                layer = QgsVectorLayer(f'Polygon?{epsg}field=File_name:string&field=Purpose:string&field=Use:string&field=Ownership:string&field=Area:string', 'XML_parcels' , "memory")
                for feature in crs_layers[crs]['Parcels']:
                    layer.dataProvider().addFeature(feature)
                if layer.featureCount()!=0:
                    layer.updateExtents()
                    layer.loadNamedStyle(os.path.join(os.path.dirname(__file__),"Styles\\parcels.qml"))
                    layer.triggerRepaint()
                    QgsProject.instance().addMapLayer(layer, False)
                    group.addLayer(layer)
                    layers_arr.append(layer)
                    print('\t\tСтворюю шар з ділянками в групі.')
            else:
                print("\t\tОб'єкти земельних ділянок  відсутні.")
            layer=None

        window.close()
        if len(layers_arr)>0: self.zoom_to_layers(layers_arr)        
           
        if len(finished_arr)>0:
            
            msgBox = QMessageBox()
            if len(err_dict["parc_err"])>0:
                parc_err=f'\r\n\r\nЗемельні ділянки з наступних файлів не були завантажені: \r\n{err_dict["parc_err"]}.'
            else:
                parc_err=''
            if len(err_dict["rest_err"])>0:
                rest_err=f'\r\n\r\nОбмеження ділянки з наступних файлів не були завантажені: \r\n{err_dict["rest_err"]}.'
            else:
                rest_err=''
            if len(err_dict["parc_inv"])>0:
                parc_inv=f'\r\n\r\nЗемельні ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["parc_inv"]}.'
            else:
                parc_inv=''
            if len(err_dict["rest_inv"])>0:
                rest_inv=f'\r\n\r\nОбмеження ділянки з наступних файлів мають не валідну геометрію: \r\n {err_dict["rest_inv"]}.'
            else:
                rest_inv=''
            if len(err_dict["parc_err"]+err_dict["rest_err"]+err_dict["parc_inv"]+err_dict["rest_inv"]+err_dict['other_err']+err_dict['other_inv'])==0:
                parc_err='\r\n\r\nВсі файли були імпортовані без помилок. Але все рівно все перевірьте!!!' 
                
            msgBox.setText(f'Оброблено {len(pathArr)} файлів.{parc_err}{rest_err}{parc_inv}{rest_inv}\r\n\r\nСтворено тимчасові шари під різні кординати, будь ласка перевірьте відповідність СК!')
            msgBox.exec()
            msgBox.setText('Плагін тестовий, перевіряйте імпорт, і давайте фідбек в чаті "JD help chat"!!!')
            msgBox.exec()
            smile={
                1:'⊂(◉‿◉)つ',
                2:'ʕ·͡ᴥ·ʔ',
                3:'ʕっ•ᴥ•ʔっ',
                4:'( ͡° ᴥ ͡°)',
                5:'( ✜︵✜ )',
                6:'(◕ᴥ◕ʋ)',
                7:'ᕕ(╭ರ╭ ͟ʖ╮•́)⊃¤=(————-',
                8:'(ﾉ◕ヮ◕)ﾉ*:・ﾟ✧',
                9:'／人◕ ‿‿ ◕人＼',
                10:' ͡°( ͡° ͜ʖ( ͡° ͜ʖ ͡°)ʖ ͡°) ͡°)',
                11:'	¯\_( ͡° ͜ʖ ͡°)_/¯',
                12:'ʕ♥ᴥ♥ʔ'
            }
            rnd=random.randint(1,500)
            if rnd in smile:
                msgBox.setText("Посміхніться, сьогодні ваш день!\r\n\r\n"+smile[rnd])
                msgBox.exec()
        else:
            msgBox = QMessageBox()
            msgBox.setText("Халепка, ні одного об'єкта не додано")
            msgBox.exec()

        


