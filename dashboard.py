from datetime import timedelta, datetime
from numpy import datetime64, float64, int32
import st_aggrid
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import streamlit as st
import pandas as pd
from zipfile import ZipFile
import requests
from bokeh.themes import built_in_themes
from bokeh.io import curdoc
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import DatetimeTickFormatter, Range1d, LinearAxis, HoverTool
import wget

st.session_state.events = None
st.session_state.tokens = None
st.session_state.addresses = None
st.session_state.slug = None

st.set_page_config(
     page_title="OpenSea OpenData",
     page_icon= "https://www.oceanmissions.com/wp-content/uploads/2021/09/400x400_rounded-150x150.png",
     layout="wide",
     initial_sidebar_state="expanded",
     menu_items={
         'Get Help': None,
         'Report a bug': None,
         'About': "We fight to bring vowels back!"
     }
 )

st.markdown( #removes the arrows from metric
                """
                <style>
                [data-testid="stMetricDelta"] svg {
                    display: none;
                }                
                </style>
                """,
                unsafe_allow_html=True,
            )

custom_css = {
            ".ag-center-cols-clipper a:link" : {"color":" #FF008E"},
            ".ag-center-cols-clipper a:visited" : {"color":" #FF008E"},
            ".ag-center-cols-clipper a:hover" : {"color":" #590696","text-decoration": "dotted"},
            ".ag-theme-streamlit .ag-root-wrapper" : {"border" : "none"},
            ".ag-theme-streamlit .ag-row" : {"border-bottom" : "none"},
            ".ag-theme-streamlit .ag-header" : { "border-bottom-color" : "#FF008E", "border-bottom-width": "2px", "background-color" : "#590696"},
            ".ag-header-cell-text" : {"font-weight" : "bold"}
        }
       
global lotsaoffers
lotsaoffers = False

offershoverlabel = " offers"
if lotsaoffers:
    offershoverlabel = "k offers"

params = {}

#region Functions

def GetStats(slug):
    url = f"https://api.opensea.io/api/v1/collection/{slug}"
    headers = { "Accept": "application/json" }
    data = requests.get(url, params=params, headers=headers).json()
    return data['collection']['stats'], data['collection']['name'], data['collection']['primary_asset_contracts'][0]['address']

def HumanFormat(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(num, round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

def EventsChart(events):
    eventsdata = events[['Date','Withdrawn Bids','Cancelled Listings','New Listings','Offers','Collection Offers','Sales','Transfers','Bids','Floor']]
    posevents = ['Collection Offers','Bids','New Listings','Transfers','Sales'] 
    colors = ['#b021ce','#44cce2', '#FA26A0', '#892CDC', '#54E346'] #FFF600
    
    p = figure(
        title = None,
        x_axis_type = "datetime",
        sizing_mode = "stretch_width",
        plot_height = 600,
        background_fill_color = '#2c2342',
        background_fill_alpha = 0
    )
    # Offers area
    start = -0.06 * (events['Offers'].max() - events['Offers'].min())
    maxoffers = events['Offers'].max() 
    end = maxoffers + 100 - maxoffers % 100
    p.extra_y_ranges = {"foo": Range1d(start=0, end=end)}
    p.add_layout(LinearAxis(y_range_name="foo"), 'right')

    legendOffers = "Offers"
    if lotsaoffers:
        legendOffers = "Offers (in thousands)"
    
    # offers area background
    p.varea(
        x = 'Date',
        y1 = 'Offers',
        y2 = 'Floor',
        source = eventsdata,
        color = "#83FFF6",
        legend_label = legendOffers,
        fill_alpha = 0.25,
        y_range_name="foo"
    )
    
    # bids, transfers, sales, listings, collection offers
    renderers = p.vbar_stack(
        source = eventsdata,
        stackers = posevents,
        x = 'Date',
        width = timedelta(days = 0.8),
        color = colors,
        legend_label = posevents,
        name=posevents
    )

    p.y_range.start = 0
    p.y_range.end = dayrange
    p.y_range.range_padding = 500

    for r in renderers:
        hover = HoverTool(tooltips=[
            ("","@Date{%F}"),
            ("","@$name $name")
        ],
        formatters={'@Date':'datetime'},
        renderers=[r])
        p.add_tools(hover)

    # line
    line = p.line(
        x = 'Date',
        y = 'Offers',
        source = eventsdata,
        color = "#83FFF6", #80FFDB
        line_width = 0.7,
        y_range_name="foo"
    )
    #point
    point = p.circle(
        x = 'Date',
        y = 'Offers',
        source = eventsdata,
        color = "#83FFF6",#80FFDB
        size = 5,
        y_range_name="foo"
    )

    # theme
    doc = curdoc()
    doc.theme = 'night_sky'
    doc.add_root(p)
    
    # add the hover property to the offers line axis
    toolTipsR = [ 
                    ("","@Date{%F}"),
                    ("", "@{Offers}{0.0}k offers")
                ]
    toolTipsS = [ 
                    ("","@Date{%F}"),
                    ("", "@{Offers} offers")
                ]
    if lotsaoffers:
        p.add_tools(HoverTool(renderers=[line, point],tooltips=toolTipsR, formatters={'@Date':'datetime'}))
    else:
        p.add_tools(HoverTool(renderers=[line, point],tooltips=toolTipsS, formatters={'@Date':'datetime'}))
    
    # configure datetime ticker
    p.xaxis[0].formatter = DatetimeTickFormatter(months="%b %Y")
    # cleanup
    p.toolbar.logo = None
    p.toolbar_location = "below"
    p.legend.orientation = "horizontal"
    
    
    p.legend.background_fill_color = '#2c2342'
    p.legend.background_fill_alpha = 1
    p.background_fill_color = '#2c2342'
    p.border_fill_alpha = 0
    p.outline_line_color = '#FF008E'

    p.xgrid.grid_line_color = '#FF008E'
    p.xgrid.grid_line_dash = [3, 6]
    p.ygrid.grid_line_color = '#FF008E'
    p.ygrid.grid_line_dash = [3, 6]

    p.xaxis.major_label_text_color = '#FF008E'
    p.xaxis.axis_label_text_color = '#FF008E'
    p.yaxis.major_label_text_color = '#FF008E'
    p.yaxis.axis_label_text_color = '#FF008E'

    return p

def SalesChart(size,sales):
    zerosales = size - sales
    
    collectionStack = ColumnDataSource(data=dict(
        x1=[sales],
        x2=[zerosales],
        y=[1]
    ))
    p = figure(
        title = None,
        sizing_mode = "stretch_width",
        tools="hover", 
        x_range=(0, size),
        tooltips="@$name",
        plot_height = 50,
        background_fill_alpha = 0
    )
    p.hbar_stack(
        stackers=['x1','x2'],
        height=0.8,
        color=('#FF008E','#590696'),
        source=collectionStack
    )

    # labels

    p.toolbar.logo = None
    p.toolbar_location = None

    p.background_fill_color = '#2c2342'
    p.border_fill_alpha = 0
    p.outline_line_alpha = 0

    p.xgrid.grid_line_alpha = 0
    p.ygrid.grid_line_alpha = 0

    p.yaxis.axis_line_alpha = 0
    
    p.yaxis.major_tick_line_color = None  # turn off y-axis major ticks
    p.yaxis.minor_tick_line_color = None  # turn off y-axis minor ticks
    p.yaxis.major_label_text_font_size = '0pt'  # turn off y-axis tick labels

    p.xaxis.major_tick_line_color = '#FF008E'
    p.xaxis.minor_tick_line_color = '#FF008E'
    p.xaxis.axis_line_color = '#FF008E'
    p.xaxis.axis_line_width = 0.5
    p.xaxis.major_label_text_color = '#FF008E'

    maincontainer.bokeh_chart(p)

def loadZip(file):
    with ZipFile(file, 'r') as zip:
        packfiles = zip.namelist()
    
        #load and set up the events list
        events = zip.open(packfiles[0])
        eventsList = pd.read_csv(events)
        #set type of events columns
        eventsList.columns = ['Date','Bids','Withdrawn Bids','Cancelled Listings','New Listings','Offers','Collection Offers','Sales','Transfers']
        eventsList['Date'] = eventsList['Date'].astype(datetime64)
        eventsList['Bids'] = eventsList['Bids'].astype('Int64')
        eventsList['Withdrawn Bids'] = eventsList['Withdrawn Bids'].astype('Int64')
        eventsList['Cancelled Listings'] = eventsList['Cancelled Listings'].astype('Int64')
        eventsList['New Listings'] = eventsList['New Listings'].astype('Int64')
        eventsList['Offers'] = eventsList['Offers'].astype('Int64')
        eventsList['Collection Offers'] = eventsList['Collection Offers'].astype('Int64')
        eventsList['Sales'] = eventsList['Sales'].astype('Int64')
        eventsList['Transfers'] = eventsList['Transfers'].astype('Int64')
        #check if we're dealing with a fuckton of automated offers; if so, we adjust the Offers column
        if eventsList['Offers'].max() > 10000:
            eventsList['Offers'] = eventsList['Offers'] / 1000
            eventsList.round(2)
            global lotsaoffers 
            lotsaoffers = True
        #add a Floor value to set up the area chart
        eventsList['Floor'] = eventsList['Offers'] * 0
        eventsList.set_index('Date')

        eventsRedux = eventsList.drop(['Date','Offers'], axis=1)
        maxdaily = eventsRedux.sum(axis='columns', numeric_only=True)
        maxday = maxdaily.max()
        global dayrange
        dayrange = maxday + 1000 - maxday % 1000

        # load and set up the addresses list
        addresses = zip.open(packfiles[1])
        addressesList = pd.read_csv(addresses)
        addressesList.columns = ['Address','Listings Created','Sent Tokens','Received Tokens','Bids Made','Bids Withdrawn','Offers Made','Collection Offers Made','Sales','Purchases','Collection Size']
        # set types of addresses columns
        addressesList['Listings Created'] = addressesList['Listings Created'].astype('Int64')
        addressesList['Sent Tokens'] = addressesList['Sent Tokens'].astype('Int64')
        addressesList['Received Tokens'] = addressesList['Received Tokens'].astype('Int64')
        addressesList['Bids Made'] = addressesList['Bids Made'].astype('Int64')
        addressesList['Bids Withdrawn'] = addressesList['Bids Withdrawn'].astype('Int64')
        addressesList['Offers Made'] = addressesList['Offers Made'].astype('Int64')
        addressesList['Collection Offers Made'] = addressesList['Collection Offers Made'].astype('Int64')
        addressesList['Sales'] = addressesList['Sales'].astype('Int64')
        addressesList['Purchases'] = addressesList['Purchases'].astype('Int64')
        addressesList['Collection Size'] = addressesList['Collection Size'].astype('Int64')

        # load and setup the token events list
        tokens = zip.open(packfiles[2])
        tokensList = pd.read_csv(tokens)
        tokensList.columns = ['Token', 'Bids Received', 'Bids Withdrawn', 'Cancelled Listings', 'Created Listings', 'Offers Received', 'Sales', 'Transfers','Gross Sales Value (ETH)']
        #set type of tokens columns
        #tokensList['Token'] = tokensList['Token'].astype('Int64')
        tokensList['Bids Received'] = tokensList['Bids Received'].astype('Int64')
        tokensList['Bids Withdrawn'] = tokensList['Bids Withdrawn'].astype('Int64')
        tokensList['Cancelled Listings'] = tokensList['Cancelled Listings'].astype('Int64')
        tokensList['Created Listings'] = tokensList['Created Listings'].astype('Int64')
        tokensList['Offers Received'] = tokensList['Offers Received'].astype('Int64')
        tokensList['Sales'] = tokensList['Sales'].astype('Int64')
        tokensList['Transfers'] = tokensList['Transfers'].astype('Int64')
        tokensList['Gross Sales Value (ETH)'] = tokensList['Gross Sales Value (ETH)'].astype(float64)
        
        zip.close()

    return eventsList, addressesList, tokensList

#endregion Functions

loadarea = st.empty()
with loadarea:
    loaddf = None
    package = None
    c1, c2 = st.columns(2)
    with c1:
        tokenfield = st.text_input('Insert dataset token')
        st.text('')
        loaddf = st.button("Load")   
    with c2:
        st.text('')

    if loaddf:    
        tokenurl ='https://drive.google.com/uc?id=' + tokenfield
        package = wget.download(tokenurl)

    #package  = None#st.file_uploader("Events List",  type="zip")  

    
    if package is not None:     
        zipfiles = loadZip(package)   
        stringo = str(package)
        if " " in stringo:
            st.session_state.slug = stringo[:stringo.index(" ")]
        else:
            st.session_state.slug = stringo[:stringo.index(".")]
        st.write(f"Loading {st.session_state.slug} dataset")
        
        st.session_state.events = zipfiles[0]
        st.session_state.tokens = zipfiles[2]
        st.session_state.addresses = zipfiles[1]
        collectionInfo = GetStats(st.session_state.slug)
        stats = collectionInfo[0]
        collname = collectionInfo[1]
        tokenaddress = collectionInfo[2]

        #region stats
        floorprice = stats['floor_price']
        totalvolume = HumanFormat(stats['total_volume']) 
        totalsales = int(stats['total_sales']) 
        collectionsize = int(stats['count'])
        averageprice = HumanFormat(stats['average_price'])
        owners = stats['num_owners']
        maincontainer = st.container()    
        with maincontainer:
            header = st.header(f"{collname} Collection")
            startDate = st.session_state.events['Date'].min()
            startMonth = datetime.strptime(str(startDate.month), "%m").strftime("%B")                        
            endDate = st.session_state.events['Date'].max()
            endMonth = datetime.strptime(str(endDate.month), "%m").strftime("%B")
            st.subheader(f"An exploration with data from {startMonth} {startDate.day}, {startDate.year} to {endMonth} {endDate.day}, {endDate.year}")
            
            col1, col2, col3, col4, col5, col6 = maincontainer.columns(6)
            
            col1.metric("Current floor price:", f"{floorprice}", delta="ETH", delta_color="off")
            col2.metric("Total Volume:", f"{totalvolume}", delta="ETH", delta_color="off")
            col3.metric("Total Sales:", f"{totalsales}", delta="sales", delta_color="off")
            col4.metric("Owners:", f"{owners}", delta="addresses", delta_color="off")
            col5.metric("Average Price:", f"{averageprice}", delta="ETH", delta_color="off")
            col6.metric("Collection size:", f"{collectionsize}", delta="items", delta_color="off")
            
        #endregion stats

        #region events chart
        maincontainer.subheader('Collection Activity')
        maincontainer.bokeh_chart(EventsChart(st.session_state.events),use_container_width=True)        
        #endregion events
        maincontainer.empty()
        #drop weird tokens in case it's a single drop collection
        # if collectionsize == 1:
        #         st.session_state.tokens.drop(st.session_state.tokens[st.session_state.tokens['Token'] != 1].index, inplace=True)
        
        anysales = sum(st.session_state.tokens['Sales'] > 0)
        totaltokens = st.session_state.tokens.shape[0]
        zerosales = totaltokens - anysales
        salespercent = (anysales / totaltokens) * 100
        zerospercent = ( zerosales / totaltokens) * 100

        if collectionsize > 1:
            maincontainer.subheader(f"In this period, {HumanFormat(salespercent)}% of the items of the collection have at least one sale. {HumanFormat(zerospercent)}% of the items had had no sales.")
            SalesChart(collectionsize,anysales)
        
        # if collectionsize == 1:
        #         st.session_state.tokens.drop(st.session_state.tokens[st.session_state.tokens['Token'] != 1].index, inplace=True)

        maincontainer.empty()
        maincontainer.empty()

        maincontainer.subheader("Events by Token") 
        st.session_state.tokens.sort_values(by='Token', inplace=True)
        tableContainerOne = maincontainer.container()  
        with tableContainerOne:
            gb = GridOptionsBuilder.from_dataframe(st.session_state.tokens)
            gb.configure_column(
                field = 'Token',
                headerName = "Token",
                cellRendererParams = { 
                    "tokencontract": tokenaddress 
                    },
                cellRenderer = JsCode("""function(params) {return '<a href="https://opensea.io/assets/ethereum/' + params.tokencontract + '/' + params.value + '" target="_blank">'+ params.value+'</a>'}""")
            )
            go = gb.build()
            AgGrid(st.session_state.tokens,gridOptions=go, allow_unsafe_jscode=True, theme='streamlit', fit_columns_on_grid_load=True, width='100%', suppressRowHoverHighlight=True, custom_css=custom_css)

        maincontainer.empty()
        maincontainer.empty()

        maincontainer.subheader("Events by Address") 
        tableContainerTwo = maincontainer.container()
        with tableContainerTwo:
            ga = GridOptionsBuilder.from_dataframe(st.session_state.addresses)
            
            ga.configure_column(
                field = 'Address',
                headerName = "Address",
                cellRenderer = JsCode("""function(params) {return '<a href="https://opensea.io/' + params.value + '" target="_blank">'+ params.value+'</a>'}""") ############# THE ERROR IS IN THIS LINE
            )
            go2 = ga.build()
            AgGrid(st.session_state.addresses,gridOptions=go2, allow_unsafe_jscode=True, theme='streamlit', fit_columns_on_grid_load=True, width='100%', suppressRowHoverHighlight=False,custom_css=custom_css)
