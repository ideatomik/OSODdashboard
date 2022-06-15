from datetime import timedelta
import st_aggrid
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import streamlit as st
import pandas as pd
import requests
from bokeh.themes import built_in_themes
from bokeh.io import curdoc
from bokeh.plotting import figure, ColumnDataSource
from bokeh.models import DatetimeTickFormatter, Range1d, LinearAxis, HoverTool

#TODO 
# Fill date gaps 

#streamlit run dashboard.py --theme.backgroundColor "#2c2342" --theme.secondaryBackgroundColor "#1a0d1e" --theme.primaryColor "#590696" --theme.base dark --server.maxUploadSize 2400 --server.maxMessageSize 2400


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
        
#pd.options.display.float_format = "{:,.2f}".format

#colnames = ['transaction_id','created_date','event_type','token_id','payment_symbol','eth_price','usd_price','bid_amount','from_address','to_address']
colnames = ['created_date','event_type','token_id','payment_symbol','usd_price','from_address','to_address']
#dtypes = {'transaction_id':object,'created_date':object,'event_type':object,'token_id':object,'payment_symbol':object,'eth_price':object,'usd_price':object,'bid_amount': object,'from_address':object,'to_address':object}
dtypes = {'created_date':object,'event_type':object,'token_id':object,'payment_symbol':object,'usd_price':object,'from_address':object,'to_address':object}

params = {}

#region Functions

# Load the database with series set to 'object' (it's better to load them like that first, it's faster)
@st.cache(suppress_st_warning=True, allow_output_mutation=True)
def loadDf(upload):
    with st.spinner("Loading data..."):
        df = pd.read_csv(upload, names=colnames, dtype=dtypes)
        st.session_state.thisdata = df 
    return df

# Set the datatypes for the dataframe series
@st.cache(suppress_st_warning=True)
def dtypeFix(df):
    try: #token_id
         with st.spinner(""):
            df.token_id = pd.to_numeric(df.token_id, errors="coerce")
            df.token_id = df.token_id.astype('Int64')
         loadarea.success(f"column 'token_id' converted to {df.token_id.dtype}")
    except:
         loadarea.warning("Error converting column 'token_id' to int format")
    
    # try: #eth_price
    #      with st.spinner(""):
    #         df.eth_price = pd.to_numeric(df.eth_price, errors="coerce")
    #      loadarea.success(f"column 'eth_price' converted to {df.eth_price.dtype}")
    # except:
    #      loadarea.warning("Error converting column 'eth_price' to float format")
    try: #usd_price
        with st.spinner(""):
            df.usd_price = pd.to_numeric(df.usd_price, errors="coerce")
        loadarea.success(f"column 'usd_price' converted to {df.usd_price.dtype}")
    except:
        loadarea.warning("Error converting column 'usd_price' to float format")
    # try: #bid_amount
    #     with st.spinner(""):
    #         df.bid_amount = pd.to_numeric(df.bid_amount, errors="coerce")
    #     loadarea.success(f"column 'bid_amount' converted to {df.bid_amount.dtype}")
    # except:
    #     loadarea.warning("Error converting column 'bid_amount' to float format")
    try: #created_date
        with st.spinner(""):
            df.created_date = pd.created_date = pd.to_datetime(df.created_date, format="%Y-%m-%dT%H:%M:%S.%f", errors = 'coerce')
        loadarea.success(f"column 'created_date' converted to {df.created_date.dtype}")
    except:
        loadarea.warning("Error converting column 'created_date' to date format")

    # bid_amount, set to float... figure out when to cut
    return df

# [0] = Stats, [1] = name, [2] = token address
def GetStats(slug):
    url = f"https://api.opensea.io/api/v1/collection/{slug}"
    headers = { "Accept": "application/json" } #"X-API-KEY": "9c0222976ecf45108830ba591d1f38c9" 
    data = requests.get(url, params=params, headers=headers).json()
    return data['collection']['stats'], data['collection']['name'], data['collection']['primary_asset_contracts'][0]['address']

#return the contract address, name

def HumanFormat(num, round_to=2):
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num = round(num / 1000.0, round_to)
    return '{:.{}f}{}'.format(num, round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

global lotsaoffers
lotsaoffers = False

def GetEvents():
    with st.spinner("Parsing events..."):
        df['day'] = pd.to_datetime(df['created_date']).dt.date
        eventsList = df.groupby(['day', 'event_type']).size().unstack('event_type',0).reset_index()
        if 'bid_entered' not in eventsList:
                eventsList['bid_entered'] = 0
        if 'bid_withdrawn' not in eventsList:
            eventsList['bid_withdrawn'] = 0
        if 'cancelled' not in eventsList:
            eventsList['cancelled'] = 0
        if 'created' not in eventsList:
            eventsList['created'] = 0
        if 'offer_entered' not in eventsList:
            eventsList['offer_entered'] = 0
        if 'successful' not in eventsList:
            eventsList['successful'] = 0
        if 'transfer' not in eventsList:
            eventsList['transfer'] = 0
        eventsList = eventsList[['day', 'bid_entered', 'bid_withdrawn', 'cancelled', 'created', 'offer_entered', 'successful', 'transfer']]
        eventsList.columns = ['Date','Bids','Withdrawn Bids','Cancelled Listings','New Listings','Offers','Sales','Transfers']


        #eventsList['Withdrawn Bids'] = eventsList['Withdrawn Bids'] * -1
        #eventsList['Cancelled Listings'] = eventsList['Cancelled Listings'] * -1
        if eventsList['Offers'].max() > 10000:
            eventsList['Offers'] = eventsList['Offers'] / 1000
            eventsList.round(2)
            global lotsaoffers 
            lotsaoffers = True
        eventsList['Floor'] = eventsList['Offers'] * 0
        eventsList.set_index('Date')

    return eventsList

offershoverlabel = " offers"
if lotsaoffers:
    offershoverlabel = "k offers"

def EventsChart(events):
    eventsdata = events[['Date','Withdrawn Bids','Cancelled Listings','New Listings','Offers','Sales','Transfers','Bids','Floor']]
    posevents = ['Bids','New Listings','Transfers','Sales'] 
    colors = ['#FFF600', '#FA26A0', '#892CDC', '#54E346']
    #colors = ['#B000B9', '#FF5F7E', '#FFAB4C', '#B983FF']
    
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
    p.extra_y_ranges = {"foo": Range1d(start=start, end=end)}
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
        color = "#80FFDB",
        legend_label = legendOffers,
        fill_alpha = 0.35,
        y_range_name="foo"
    )
    # bids, transfers, sales
    renderers = p.vbar_stack(
        source = eventsdata,
        stackers = posevents,
        x = 'Date',
        width = timedelta(days = 0.8),
        color = colors,
        legend_label = posevents,
        name=posevents
    )
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
        color = "#80FFDB",
        line_width = 0.7,
        y_range_name="foo"
    )
    #point
    point = p.x(
        x = 'Date',
        y = 'Offers',
        source = eventsdata,
        color = "#80FFDB",
        size = 8,
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

    st.bokeh_chart(p)

#endregion Functions

loadarea = st.empty()
with loadarea:
    loaddf = st.file_uploader("Choose a file")    

    if loaddf is not None:    
        st.write("Filename: ", loaddf.name)
        slug =  loaddf.name.partition('OMData')[0]
        collectionInfo = GetStats(slug)
        stats = collectionInfo[0]
        collname = collectionInfo[1]
        tokenaddress = collectionInfo[2]
        

        with st.spinner("Loading..."):
            data = loadDf(loaddf)
            loadarea.success("Transactions Record successfully loaded.")
            with st.spinner("Normalizing..."):
                df = dtypeFix(data)
            loadarea.success("Transactions Record successfully normalized.")
        loadarea.empty() 

        # Get the events
        events = GetEvents()

        #get the stats
        floorprice = stats['floor_price']
        totalvolume = HumanFormat(stats['total_volume']) 
        totalsales = int(stats['total_sales']) 
        collectionsize = int(stats['count'])
        averageprice = HumanFormat(stats['average_price'])
        owners = stats['num_owners']
        metricscontainer = st.container()    
        with metricscontainer:
            header = st.header(f"{collname} Collection Exploration")
            st.subheader(f"An exploration with data from {events['Date'].min()} to {events['Date'].max()}")
            #region stats
            col1, col2, col3, col4, col5, col6 = metricscontainer.columns(6)
            
            col1.metric("Current floor price:", f"{floorprice}", delta="ETH", delta_color="off")
            col2.metric("Total Volume:", f"{totalvolume}", delta="ETH", delta_color="off")
            col3.metric("Total Sales:", f"{totalsales}", delta="sales", delta_color="off")
            col4.metric("Owners:", f"{owners}", delta="addresses", delta_color="off")
            col5.metric("Average Price:", f"{averageprice}", delta="ETH", delta_color="off")
            col6.metric("Collection size:", f"{collectionsize}", delta="items", delta_color="off")
            
            #endregion stats
                
            #region events chart
            metricscontainer.subheader('Collection Activity')

            st.bokeh_chart(EventsChart(events),use_container_width=True)        
            #endregion events
            
            #region sales bar
            #This is similar to Get Events, but grouped by token_id instead
            eventsCountList = df.groupby(['token_id', 'event_type']).size().unstack('event_type',0).reset_index()
            if 'bid_entered' not in eventsCountList:
                eventsCountList['bid_entered'] = 0
            if 'bid_withdrawn' not in eventsCountList:
                eventsCountList['bid_withdrawn'] = 0
            if 'cancelled' not in eventsCountList:
                eventsCountList['cancelled'] = 0
            if 'created' not in eventsCountList:
                eventsCountList['created'] = 0
            if 'offer_entered' not in eventsCountList:
                eventsCountList['offer_entered'] = 0
            if 'successful' not in eventsCountList:
                eventsCountList['successful'] = 0
            if 'transfer' not in eventsCountList:
                eventsCountList['transfer'] = 0
            eventsCountList = eventsCountList[['token_id', 'bid_entered', 'bid_withdrawn', 'cancelled', 'created', 'offer_entered', 'successful', 'transfer']]
            eventsCountList.columns = ['Token', 'Bids Received', 'Bids Withdrawn', 'Cancelled Listings', 'Created Listings', 'Offers Received', 'Sales', 'Transfers']
            
            anysales = sum(eventsCountList['Sales'] > 0)
            totaltokens = eventsCountList.shape[0]
            zerosales = totaltokens - anysales
            salespercent = (anysales / totaltokens) * 100
            zerospercent = ( zerosales / totaltokens) * 100

            if collectionsize > 1:
                st.subheader(f"In this period, {HumanFormat(salespercent)}% of the items of the collection have at least one sale. {HumanFormat(zerospercent)}% of the items haven't been sold.")
                SalesChart(collectionsize,anysales)
            #endregion

            #region Tokens Table
            successfulList = df.query("event_type == 'successful'")
            grosssales = successfulList.groupby('token_id')['usd_price'].sum().reset_index()
            grosssales.columns = ['Token','Gross Value (USD)']  

            tokensList = pd.merge(eventsCountList, grosssales, on="Token", how="left")
            tokensList.fillna(0,inplace=True)
            tokensList['Gross Value (USD)'] = tokensList['Gross Value (USD)'].astype(float).round(2)   
            if collectionsize == 1:
                tokensList.drop(tokensList[tokensList['Token'] != 1].index, inplace=True)

            st.empty()
            st.subheader("Events by Token")        
            gb = GridOptionsBuilder.from_dataframe(tokensList)
            gb.configure_column(
                field = 'Token',
                headerName = "Token",
                cellRendererParams = { 
                    "tokencontract": tokenaddress 
                    },
                cellRenderer = JsCode("""function(params) {return '<a href="https://opensea.io/assets/ethereum/' + params.tokencontract + '/' + params.value + '" target="_blank">'+ params.value+'</a>'}""")
                
            )
            
            go = gb.build()
            AgGrid(tokensList,gridOptions=go, allow_unsafe_jscode=True, theme='streamlit', fit_columns_on_grid_load=True, width='100%', suppressRowHoverHighlight=True, custom_css=custom_css)
            #endregion

            st.empty()
            st.empty()   

            addressFromList = df.groupby(['from_address', 'event_type']).size().unstack('event_type',0).reset_index()      
            
            if 'transfer' not in addressFromList:
                addressFromList['transfer'] = 0     
            if 'created' not in addressFromList:
                addressFromList['created'] = 0 
            if 'offer_entered' not in addressFromList:
                addressFromList['offer_entered'] = 0
            if 'bid_withdrawn' not in addressFromList:
                addressFromList['bid_withdrawn'] = 0 
            if 'bid_entered' not in addressFromList:
                addressFromList['bid_entered'] = 0  
            if 'successful' not in addressFromList:
                addressFromList['successful'] = 0 
            
            addressFromList = addressFromList[['from_address','transfer','created','offer_entered','bid_entered','bid_withdrawn','successful']]
            addressFromList.columns = ['Address','Sent Tokens','Listings Created','Offers Made','Bids Made','Bids Withdrawn', 'Sales']
            
            addressToList = df.groupby(['to_address', 'event_type']).size().unstack('event_type',0).reset_index()
            if 'successful' not in addressToList:
                addressToList['successful'] = 0
            addressToList.columns = ['Address','Received Tokens','Purchases']
            
            mergedAddresses = pd.merge(addressFromList,addressToList, on="Address", how="left")
            mergedAddresses.fillna(0,inplace=True)
            mergedAddresses['Received Tokens'] = mergedAddresses['Received Tokens'].astype(int)
            
            mergedAddresses = mergedAddresses[['Address','Listings Created','Sent Tokens','Received Tokens','Bids Made','Bids Withdrawn','Offers Made','Sales','Purchases']] #remove sales and purchases

            mergedAddresses['Collection Size'] = mergedAddresses['Received Tokens'] - mergedAddresses['Sent Tokens']

            mergedAddresses.sort_values(by='Collection Size', inplace=True, ascending=False)

            ga = GridOptionsBuilder.from_dataframe(mergedAddresses)
            
            ga.configure_column(
                field = 'Address',
                headerName = "Address",
                cellRenderer = JsCode("""function(params) {return '<a href="https://opensea.io/' + params.value + '" target="_blank">'+ params.value+'</a>'}""") ############# THE ERROR IS IN THIS LINE
            )
            go2 = ga.build()

            st.subheader("Events by Address")  
            
            AgGrid(mergedAddresses,gridOptions=go2, allow_unsafe_jscode=True, theme='streamlit', fit_columns_on_grid_load=True, width='100%', suppressRowHoverHighlight=False,custom_css=custom_css)
