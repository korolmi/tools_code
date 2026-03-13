"""
Модуль собран руками из ноутбука, не стоит особо менять
"""

def _getCteName(ln):
    """ эта функция инкапсулирует функциональность проверки строки на начало CTE 
    возвращает имя CTE, если строка является его началом, или None
    """

    CTE_START = " as (" # с этого начинается CTE

    if ln.lower().find(CTE_START)>0: # начало CTE
        return ln.lower().split(CTE_START)[0].split()[-1].strip().replace(",","")
    else:
        return None

def _isAllCteEnd(ln):
    """ эта функция инкапсулирует способ поиска завершения всех CTE """
    
    ALL_END = "-- END CTES" # этим заканчиваются CTE, после этого идет финальный запрос (select)

    return ln.find(ALL_END)>=0

def getCteSrc(sql,debug=False):
    """
    Формирует словарь CTE
    * ключ: имя CTE
    * значение: код CTE
    использует предположения о правилах оформления CTE, см. функции выше
    сам запрос - финальный - добавляет как CTE с именем FinQ
    """

    res = {}
    
    sqlLines = sql.split("\n") # список, чтобы можно было "ходить вверх"
    
    # идем по строкам и ищем начало CTE
    curCteLines = []
    prevCte = None
    notFirst = False
    for lineNo in range(len(sqlLines)):
        cteName = _getCteName(sqlLines[lineNo]) # используем предположение об офомлении первой строки CTE
        if cteName is not None: # начало CTE
            if debug:
                print("CTE:",cteName)
            # ищем конец предыдущего CTE
            if notFirst: # для перевого ничего делать не надо
                for i in range(1,10): # 10 - просто константа на сколько строк вверх подниматься (пропускаем комментарии и пустые строки)
                    if sqlLines[lineNo-i].find(")")>=0: # конец предыдущего CTE
                        break
                # удаляем лишние строки
                curCteLines = curCteLines[:-i]
                res[prevCte] = curCteLines # добавляем тело предыдущего CTE
            else:
                notFirst = True
            prevCte = cteName
            curCteLines = [ sqlLines[lineNo].split("(")[1] ] # в начало следующего CTE добавляем все после открывающей скобки
            continue 
            
        if _isAllCteEnd(sqlLines[lineNo]): # конец всех CTE - используем предпоположения об оформлении
            for i in range(1,10): # 10 - просто константа на сколько строк вверх подниматься (пропускаем комментарии и пустые строки)
                if sqlLines[lineNo-i].find(")")>=0: # конец предыдущего CTE
                    break
            res[prevCte] = curCteLines[:-i] # убираем завершающую скобку
            curCteLines = []
            continue

        # добавляем строку к блоку строк CTE
        curCteLines.append(sqlLines[lineNo])

    # оформляем сам запрос в виде CTE с именем FinQ    
    res["FinQ"] = curCteLines
    
    return res

def getCteDeps(cteSrc,debug=False):
    """ 
    Формирует словарь зависимостей: 
    * ключ: CTE
    * значение: список всего что встретилось в теле CTE в части from и join
    """

    SEPS = [ "from ", "join " ]

    res = {}
    for k,v in cteSrc.items():
        deps = []
        if debug:
            print("processing", k)
        for ln in v:
            for sep in SEPS:
                spLine = ln.split("--")[0].lower().replace("\t","    ") # канонически все в нижний регистр, табуляцю заменяем на пробел
                if spLine.find(sep)>=0: # нашли, проверим на "лексемность"
                    sepPos = spLine.find(sep)
                    if sepPos==0 or spLine[sepPos-1]==" ": # либо разделитель находится в начале строки, либо слева от него пробельный символ
                        dep = spLine.split(sep)[1].split()[0]
                        if dep not in deps:
                            deps.append(dep)
        res[k] = deps    
    
    return res

def _genSeq(cte,cteDeps,cteExcl):
    """
    Строит последовательность CTE в результирующем запросе с учетом зависимостей и исключений
    """

    depSet = set() # набор оставшихся зависимостей
    res = [] # список опубликованного
    curCte = cte
    while True:
        curDeps = [] # зависимости текущего цте
        depSet.add(curCte) # текущий элемент тоже зависимость
        # print(depSet)
        if curCte not in cteExcl.keys(): # у материализованного CTE нет зависимостей, не добавляем их 
            for dep in [ d for d in cteDeps[curCte] if d.find(".")<=0 ]: # только CTE
                if dep not in res: # если этот цте еще не публиковали - добавляем в текущие зависимости
                    curDeps.append(dep)
        if len(curDeps)>0: # есть неопубликованные зависимости, добавляем их в список зависимостей
            for d in curDeps:
                depSet.add(d)
        else: # можно публиковать
            res.append(curCte)
            depSet.remove(curCte)
            # print("Added",curCte)
        if len(depSet)==0:
            break
        curCte = depSet.pop() # вытолкнули, но вверху опять вставим...

    return res

def genCte(cte,cteSrc,cteDeps,cteExcl={}):
    """ 
    генерирует код запроса, формирующего данные нужного cte 
    параметры:

    cte: собственно имя CTE
    cteSrc: словарь кода CTE
    cteDeps: словарь зависимостей
    cteExcl: словарь имен материализаций (ключи - исключаемые из рассмотрения CTE)
    """
    seqList = _genSeq(cte,cteDeps,cteExcl) # список публикации

    res = [ ]
    pref = ""
    for i,c in enumerate(seqList):
        remCtes = len(seqList)-(i+1)
        if remCtes>0: # для последнего будет особый случай
            if i>0: # для всех CTE кроме первого
                pref = ","
            else:                
                pref = "with"
        srcList = cteExcl[c] if c in cteExcl else cteSrc[c]
        for j,ln in enumerate(srcList):
            if j==0: # вставляем заголовок CTE
                if remCtes==0: # но не для последнего CTE
                    suff = ""
                else:
                    suff = f" {c} as ("
            else:
                suff = ""
                pref = ""
            res.append(f"{pref} {suff} {ln}")
        if remCtes!=0:
            res.append(") ------------------------------------------")
        
    return res

import graphviz

def genGraph(cteDeps,bigTables = [],matCtes = []):
    
    dot = graphviz.Digraph(node_attr={'shape': 'box'})

    for k in cteDeps.keys():
        if k in matCtes:
            dot.node(k,k,fillcolor='yellow', style='filled')  
        else:
            dot.node(k,k)

    tabSet = set()
    for ndFrom,v in cteDeps.items():
        for ndTo in v:
            if ndTo.find(".")>0:
                tabName = ndTo.split(".")[1]
                if tabName in bigTables: # большая таблица - рисуем
                    if tabName not in tabSet:
                        dot.node(tabName, tabName, fillcolor='lightblue', style='filled')  
                        tabSet.add(tabName)
                    dot.edge(tabName,ndFrom)       
                continue
            dot.edge(ndTo,ndFrom)

    return dot

