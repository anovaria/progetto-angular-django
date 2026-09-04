/*
    TEST COMPATIBILITA' ETL vs AMBIENTE ORACLE MAJOR RELEASE (GC.CEN.TEST / GC.STK.TEST)
    ======================================================================================
    Scopo: verificare che le query Oracle dentro le sp_Create_* del portale
    (che scrivono le tabelle base lette da Django su srviisnew) girino ancora
    senza errori contro l'ambiente Oracle di test della major release TESI.

    NON tocca nessuna tabella reale: ogni blocco scrive SOLO in una #temp table
    di sessione, che sparisce alla chiusura della query/connessione.

    Esegui l'intero script (F5) in SSMS collegato a srviisnew, con contesto
    Db_GoldReport (il primo USE lo imposta). Ogni blocco è in TRY/CATCH: un
    errore su un blocco non ferma gli altri. Guarda la tab "Messages" per
    l'esito di ognuno (OK - righe: N  /  ERRORE: ...).

    NOTE APERTE (non risolte da questo script, da verificare a parte con TESI):
    - t_przacq (parte t_przacq_dash) usa un DB LINK ORACLE INTERNO 'DASHGCIDAC'
      dentro la query eseguita via GOLDPROD. Non sappiamo se GC.CEN.TEST abbia
      un equivalente: se questo blocco fallisce con "DASHGCIDAC" nel messaggio,
      il problema è quel link, non GC.CEN.TEST in se'.
    - t_stockpick usa DB LINK ORACLE INTERNI 'DBL_CENTRAL5.GROSCIDAC.local'
      dentro la query eseguita via GOLDSTK. Stesso discorso: se fallisce
      nominando quel link, va chiesto a TESI se esiste un pari in GC.STK.TEST.
    - v_abbigliamento: la SP reale fa anche un REFRESH della materialized view
      Oracle (scrittura). Qui testiamo SOLO la lettura di mw_abbigliamento,
      di proposito, per restare in sola lettura.
*/

USE Db_GoldReport;
GO

PRINT '=== 1/23 t_masterData ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_masterdata') IS NOT NULL DROP TABLE #test_t_masterdata;
    SELECT *
    INTO #test_t_masterdata
    FROM OPENQUERY([GC.CEN.TEST],'with Venduti as (
        select distinct /*+ materialize*/
               arucinr VENCEXR, max(stmdmvt) ultima_vendita
          from stomvt, ARTUL
         where stmtmvt = 150
           and stmmotf not in (20,520)
           and stmcinl = arucinl
           group by arucinr),
        Resi as (
        select distinct /*+ materialize*/
               arucinr RESCEXR, SUM(STMVAL) Qta_reso, sum(STMVPV) Val_reso
          from stomvt, ARTUL
         where stmtmvt = 113
           and stmcinl = arucinl
           and stmdmvt = trunc(sysdate - 1)
           group by arucinr),
        Ordinati as (
        select distinct /*+ materialize*/
               arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine, DCDDLIV dta_Cons,  sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
          from cdedetcde, ARTUL
         where DCDCINL = arucinl
         and dcdetat = 5
           group by arucinr, DCDDLIV),
        Ricevuti as (
        select distinct /*+ materialize*/
               arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
          from stodetre, ARTUL
         where SDRCINLS = arucinl
           group by arucinr)
        select to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
                  TSSRENIV1 Settore,
                  TSSRENIV2 Reparto,
                  TSSRELIBN2 DescRep,
                  TSSRENIV3 SottoReparto,
                  TSSRELIBN3 DescSRep,
                      TSSRENIV4 Famiglia,
                  TSSRELIBN4 DescFam,
                  pkfoudgene.get_cnuf(0,aracfin) codForn,
                  pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn,
                      PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
                  PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,
                      ararefc codArtfo,
                  ARVCEXR codArt,
                  ARTTYPP TipoA,
                  pkstrucobj.get_desc(0,arvcinr,''IT'') descrArt,
                      PKARTUL.GETLIBLTYPEUL(1, ARACINL, ''IT'') Gest,
                  PKARTSTOCK.RECUPCOEFFUVC(1, ARuCINL)  PzXCart,
                  PKPRIXVENTE.GET_PRIX_VENTE(0,ARVCINV,10001,3,TRUNC(SYSDATE)) prz_vend,
                  NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 10001, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (sysdate+1)), 0) GIACENZA_PDV,
                  NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 901, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (SYSDATE+1)), 0)/PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) GIACENZA_DEPOSITO,
                  qta_in_ordine,
                  to_char(ultimo_Ordine,''dd/mm/yyyy'') ultimo_Ordine,
                  to_char(dta_Cons,''dd/mm/yyyy'') Data_Consegna,
                  to_char(ULTIMA_VENDITA,''dd/mm/yyyy'') ultima_vendita,
                  to_char(ultimo_Ricevimento, ''dd/mm/yyyy'') ultimo_ricevimento,
                  Qta_reso,
                  Val_reso,
                   (select listagg(OPLCEXOPR,'', '') within group (order by 1)
                     from tst_pma_articolo,oprplan
                    where TSARPTPNOPR = oplnopr
                      and TSARPCINV = arvcinv
                      and trunc(sysdate) between OPLDDEBV and OPLDFINV) CodPromo,
                   AATCATT  S,
                   (select AATCATT||AATVALN from artattri attri1
                    where
                    attri1.aatcinr = arvcinr
                    and aatccla =''TCOL''
                    and trunc(sysdate) between AATDDEB and AATDFIN ) TCOL,
                    ARTTVAV iva,
                  ARACEXVL VL,
                  (select distinct cast(min(TSARPPRZOFF) as dec (10,2)) PrzPromo
                     from tst_pma_articolo,oprplan
                    where TSARPTPNOPR = oplnopr
                      and TSARPCINV = arvcinv
                      and trunc(sysdate) between OPLDDEBV and OPLDFINV
                      and TSARPPRZOFF is not null) PrzPromo,
                  arutypul ULC,
                  NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 902, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (SYSDATE+1)), 0)/PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) Giac_DepCared
             from Venduti, ordinati, Ricevuti, Resi,
                  artsite, artuv, tsv_strucrel, artuc, artattri, artrac, artul
            where 1=1
              and aracinr = arvcinr
              and artcinr = aracinr
              and artcinr = ARUCINR
              and ARASEQVL = ARUSEQVL
               and arutypul =''41''
              and pkfoudgene.get_foutype(0,aracfin) <> 3
              and trunc(sysdate) between araddeb and aradfin
              and aratfou = 1
              and arvcinr = VENCEXR (+)
              and arvcinr = ORDCEXR (+)
              and arvcinr = RICCEXR (+)
              and arvcinr = RESCEXR (+)
              and arvcinv = sitcinv
              and arvcinr = TSSRECINR
              and sitfsup = 0
              and aatcinr = arvcinr
              and aatccla = ''SARGC''
              and trunc(sysdate) between AATDDEB and AATDFIN  ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_masterdata;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 2/23 t_MasterDataAll (t_m1 - TCOL) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_m1') IS NOT NULL DROP TABLE #test_t_m1;
    SELECT * INTO #test_t_m1 FROM OPENQUERY ([GC.CEN.TEST],'select artcexr codart,
                    MAX(AATCATT) KEEP (DENSE_RANK LAST ORDER BY AATDFIN) T1,
                    MAX(AATVALN) KEEP (DENSE_RANK LAST ORDER BY AATDFIN) T2,
                    max(AATDFIN) dtafine
                from artrac, artattri, tsv_strucrel
                where 1=1
                and artcinr = aatcinr
                and AATCCLA = ''TCOL''
                and artcexr = TSSRECEXR
                and TSSRENIV1 = ''3''
                group by artcexr');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_m1;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 2b/23 t_MasterDataAll (t_m2 - principale) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_m2') IS NOT NULL DROP TABLE #test_t_m2;
    SELECT * INTO #test_t_m2 FROM OPENQUERY([GC.CEN.TEST],'with Inventario as (select artcexr codart, max(DINDINV) ultimoinventario
                from artrac a left join invdetinv i on a.artcinr = i.dincinr
                where 1=1  group by artcexr )
    select distinct to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
    TSSRENIV1 sett, TSSRENIV2 Rep, TSSRELIBN2 DescrRep, TSSRENIV3 Srep, TSSRELIBN3 DescrSrep,
    TSSRENIV4 fam, TSSRELIBN4 DescrFam, ARASITE sito,
    aratfou Foprinc,
    pkfoudgene.get_cnuf(0,aracfin) codForn,
    pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn,
    PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
    PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,
    TSK_FLODASH.GET_LINEA_PRODOTTO(ARTCEXR,TRUNC(SYSDATE)) LINEA_PRODOTTO,
    PKATTRIVAL.GETLIBELLELONGATTRIBUT(0,''ACQ'',TSK_FLODASH.GET_LINEA_PRODOTTO(ARTCEXR,TRUNC(SYSDATE)),''IT'') Descr_Linea,
    ararefc codArtfo,
    artcexr codArt,
    AATCATT Stato,
    pkstrucobj.get_desc(0,arAcinr,''IT'') descrArt,
    TAPPBRUT PrAcq,
    TAPCTVA Iva,
    PKPRIXVENTE.GET_PRIX_VENTE(0,ARVCINV,10001,3,TRUNC(SYSDATE)) prz_vend,
    ARCTCOD tipoEan,
    ARCIETI EticEan,
    arccode Ean,
    arccode EanA,
    PKARTUL.GETLIBLTYPEUL(1, ARACINL, ''IT'') Gest,
    PKPARPOSTES.GET_POSTLIBL(0,0,''1036'',ARTUFAC,''IT'') Gest_Acq,
    ARLCEXVL Vl,
              (select distinct cast(min(TSARPPRZOFF) as dec (10,2)) PrzPromo
                 from tst_pma_articolo,oprplan
                where TSARPTPNOPR = oplnopr
                  and TSARPCINV = arvcinv
                  and trunc(sysdate) between OPLDDEBV and OPLDFINV
                  and TSARPPRZOFF is not null) PrzPromo,
    ALOSMAG cons,
    ''collo'' D1,''1'' PzXCrt, ''Strato'' D2, ''1'' strato,''palle'' D3, ''1'' pallet,
    to_char(ultimoinventario,''dd/mm/yyyy'') Dta_invent
    from artrac, tsv_strucrel, artuc, TARPRIX, artcoca, artattri,  artul, artvl, ARTASENT, artuv, inventario
    where artcexr = TSSRECEXR
    and artcexr = inventario.codart (+)
    and artcinr = aracinr
    and ARADFIN = (select max(a.ARADFIN) from artuc a where a.aracinr = artcinr )
    and ARACCIN = TAPCCIN
    and ARASEQVL = TAPSEQVL
    and artcinr = tapcinr
    and TAPDFIN = (select max(t.TAPDFIN) from tarprix t where t.tapcinr = artcinr and t.tapccin = araccin )
    and artcinr = ARCCINR
    and trunc(sysdate) between ARCDDEB and ARCDFIN
    and artcinr  = AATCINR
    and trunc(sysdate) between AATDDEB and AATDFIN
    and AATCCLA = ''SARGC''
    and ARCTCOD not in (''5'')
    and artcinr = ARUCINR
    and artcinr =ARLCINR
    and ARASEQVL = ARLSEQVL
    and artcinr = ALOCINR (+)
    and trunc(sysdate) between ALODDEB (+) and ALODFIN (+)
    and artcinr = ARVCINR
    and ARLETAT = 1
    order by TSSRENIV1, TSSRENIV2, TSSRENIV3, artcexr');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_m2;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 3/23 MasterDataCategory (query principale) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_masterdatacategory') IS NOT NULL DROP TABLE #test_masterdatacategory;
    SELECT * INTO #test_masterdatacategory
        FROM OPENQUERY([GC.CEN.TEST],'with a as (select distinct * from (select distinct TSAVMANNO Anno, TSAVMMESE mese,TSAVMACOD codArtd,
        (TSAVMVENQTA ) QtaV    from tst_artvenmes_ext where 1=1 and TSAVMANNO in(extract(year from sysdate),extract(year from sysdate)-1))
         PIVOT  (  sum(QtaV)   FOR Mese  in (1 as "Gennaio",2 as "Febbraio",3 as "Marzo",4 as "Aprile",5 as "Maggio",6 as "Giugno",
         7 as "Luglio",8 as "Agosto",9 as "Settembre",10 as "Ottobre",11 as "Novembre",12 as "Dicembre"))),
        b as (select distinct codart as codartp, varacq,nettonetto, iva from sil_przacq_V2  )
        select distinct  to_char(sysdate,''dd/mm/yy'')dtaggio, TSSRENIV1 Sett, TSSRENIV2 Rep,     TSSRELIBN2 Descr_reparto, TSSRENIV3 Srep, TSSRELIBN3 Descr_Sottoreparto,
         TSSRENIV4 Fami, TSSRELIBN4 Descr_Famiglia,arasite sito, aratfou Fop, PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,  PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,
         (select AATVALNUM from artattri where aatcinr = artcinr and aatccla = ''RIOCCOM''  and trunc(sysdate) between AATDDEB and AATDFIN) RiocCom,
         ARTTYPP tipoArt, ARTETAT StatoArt,
         (select AATVALNUM from artattri where aatcinr = artcinr and aatccla = ''CORSIA''  and trunc(sysdate+1) between AATDDEB and AATDFIN) Corsia_gold,
         (select AATVALNUM from artattri where aatcinr = artcinr and aatccla = ''CAMPATA''  and trunc(sysdate+1) between AATDDEB and AATDFIN) Campata_gold,
         (select AATVALNUM from artattri where aatcinr = artcinr and aatccla = ''NRFACING''  and trunc(sysdate+1) between AATDDEB and AATDFIN) Facing_gold,
         (select AATVALNUM from artattri where aatcinr = artcinr and aatccla = ''QTAMAX''  and trunc(sysdate+1) between AATDDEB and AATDFIN) qtamax,
         ARAREFC codartfo,TSARUCEXR codart, pkstrucobj.get_desc(0,TSSRECINR,''IT'' ) descrArt,
         artdlim ggScad, AATCATT stato, ARCTCOD tipoEan,ARCIETI princ, ARCCODE ean,
         TSARUCEXVL vl, TSARUUXI pzxCrt, TSARUCXS colliXStrato, TSARUSXP StratiXpallet ,TSARUPXP collipallet,
         TSARUPBRUp pesoPezzo, TSARUPBRUP pesoCollo, TSARULONGC lungh, TSARUHAUTC alt,TSARULARGC largh,   round((TSARULONGC * TSARUHAUTC * TSARULARGC)/1000000,3)  volColloM3,
         SITOC, VLC , ULC, GEST, con.PZXCART,nvl((select PKARTSTOCK.RECUPCOEFFUVC(1, arucinl)  from artul where arucinr = aracinr and   arutypul=ARACEXTA and araseqvl = aruseqvl ),PKARTSTOCK.RECUPCOEFFUVC(1, aracinl)) qtaminacq,
         indirizzo_picking , baricentro, anno,  "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
         varacq, nettonetto nettonettoDash,iva, PKPRIXVENTE.GET_PRIX_VENTE(0,ARVCINV,10001,3,TRUNC(SYSDATE)) prz_vend
        from tsv_artulul inner join tsv_strucrel on TSARUCEXR = TSSRECEXR
                                   inner join artrac a  on TSSRECEXR = artcexr
                                   inner join artuc c on artcinr = aracinr
                                   inner join artattri t on artcinr = AATCINR
                                   left join mw_cons901 con on artcexr = codarticolo and ARACEXVL = TSARUCEXVL
                                   left join tsv_art_pick  ts on artcexr = ts.codice_articolo
                                   inner join artcoca ca on artcinr = ARCCINR and trunc(sysdate) between ARCDDEB and ARCDFIN
                                   left join a va on artcexr = va.codartd
                                   left join b pr on artcexr = codartp
                                   left join artuv vu on artcinr = arvcinr
        where 1=1  and TSARUETAT = ''1''  and ARASEQVL= TSARUSEQVL and trunc(sysdate) between araddeb and aradfin
             and  PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) not in (''901'') and substr(PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN),1,1) not in (''*'') and AATCCLA =''SARGC''   and trunc(sysdate) between AATDDEB and AATDFIN
             ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_masterdatacategory;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 3b/23 MasterDataCategory (query marca/qualita) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_marca') IS NOT NULL DROP TABLE #test_marca;
    SELECT * INTO #test_marca FROM OPENQUERY([GC.CEN.TEST],'select distinct artcexr codart, CASE WHEN AATCATT = ''2'' Then ''noiEvoi'' else '''' end marca
    from artrac inner join artattri on artcinr = AATCINR
    where 1=1 and AATCATT =''2''
    and aatccla =''QUALITA'' and trunc(sysdate+1) between AATDDEB and AATDFIN');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_marca;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 4/23 t_PianoPromo ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_pianopromo') IS NOT NULL DROP TABLE #test_t_pianopromo;
    SELECT * INTO #test_t_pianopromo
        FROM OPENQUERY([GC.CEN.TEST],'select
            to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
            TSPIANOPR codiceGold,
            tspiacexopr PIANO,
            TOPLDESC DESCRIZIONE,
            to_char(oplddebcdm,''dd/mm/yyyy'') INIZIO_SELLIN,
            to_char(opldfincdm,''dd/mm/yyyy'') FINE_SELLIN,
            to_char(oplddebv,''dd/mm/yyyy'')  INIZIO_SELLOUT,
            to_char(opldfinv,''dd/mm/yyyy'')  FINE_SELLOUT,
            TSPIANOPR CodPiano
        from tst_pma_piano,oprplan,tra_oprplan
        where tspianopr = OPLNOPR
        and oplddebv > TRUNC(SYSDATE-180)
        and OPLNOPR = TOPLNOPR
        and langue = ''IT''');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_pianopromo;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 5/23 t_SARGC ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_sargc') IS NOT NULL DROP TABLE #test_t_sargc;
    SELECT * INTO #test_t_sargc FROM OPENQUERY([GC.CEN.TEST],'select distinct
     to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
     TSSRENIV1 s,
     TSSRENIV2 Rep,
     TSSRENIV3 Srep,
     TSSRENIV4 Fam,
     artcexr CodArt,
     pkstrucobj.get_desc(0,ARTUL.ARUCINR,''IT'') DESCRIZIONE_ART,
     NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 10001, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARuCINR, ARuSEQVL), TRUNC (sysdate+1)), 0) GiacPDV,
     NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 901, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (SYSDATE+1)), 0) GiacDepColli,
     AATCATT St,
     AATCCLA Cod,
     AATVALN Alpha,
    to_char(AATDDEB, ''dd/mm/yyyy'') DtaIni,
    to_char(AATDFIN, ''dd/mm/yyyy'') DtaFine,
    to_char(sysdate, ''dd/mm/yyyy'') DtaCh
     from ARTRAC, artul, artattri, tsv_strucrel, artuc
     where
     TSSRECEXR = artcexr
     and artcinr = ARUCINR
     and aatccla = ''SARGC''
     and AATCINR = artcinr
     and trunc(sysdate ) between AATDDEB and AATDFIN
     and AATDFIN > trunc(sysdate)
     and artcinr = ARACINR
     and TSSRENIV1 in(''1'',''2'',''3'',''4'',''6'')');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_sargc;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 6/23 t_t_Ean ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_t_ean') IS NOT NULL DROP TABLE #test_t_t_ean;
    SELECT * INTO #test_t_t_ean
        FROM OPENQUERY([GC.CEN.TEST],'select to_char(sysdate,''dd/mm/yyyy'') dtaaggio,artcexr codart,
                                    pkstrucobj.get_desc(0,artcinr,''IT'') descrArt,
                                    ARCCODE Ean,
                                    case when ARCTCOD = ''6'' then ''00000''|| ARCCODE
                                    else ARCCODE END as EanA,
                                    ARCTCOD tipo, ARCIETI Princ, ARCETAT StEan,
                                    to_char(ARCDDEB,''DD/MM/RRRR'') DtaIni,
                                    to_char(ARCDFIN,''DD/MM/RRRR'') Stafine,
                                    PKPARPOSTES.GET_POSTLIBL(0,0,''1036'',ARTUFAC,''IT'') Gest
                                    from artrac, artcoca
                                    where artcinr = arccinr
                                    and trunc(sysdate) between ARCDDEB  and  ARCDFIN');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_t_ean;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 7/23 t_InvendutiTot (Fase1 - Sett.1, con vendite) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_invtot_fase1') IS NOT NULL DROP TABLE #test_invtot_fase1;
    SELECT * INTO #test_invtot_fase1
        FROM Openquery([GC.CEN.TEST],'with
        Vend as (select distinct arucinr VENCEXR, max(stmdmvt) ultima_vendita
                  from stomvt, ARTUL
                  where stmtmvt = 150
                     and stmmotf not in (20,520)
                     and stmcinl = arucinl
                  group by arucinr ),
        Ordinati as (select distinct arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine, DCDDLIV dta_Cons,
                         sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
                    from cdedetcde, ARTUL
                    where DCDCINL = arucinl
                        and dcdetat = 5
                        and DCDDLIV > =  trunc(sysdate)
                    group by arucinr, DCDDLIV),
        Ricevuti as ( select distinct arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
                    from stodetre, ARTUL
                    where SDRCINLS = arucinl
                    group by arucinr),
        Inventario as (select artcexr codart, max(DINDINV) ultimoinventario
                from artrac a left join invdetinv i on a.artcinr = i.dincinr
                where 1=1
                  and DINDINV not in(''2024/03/31'')
                group by artcexr )
        select to_char(sysdate,''dd/mm/yyyy'') dtaaggio,ARTDCRE dtacreaz,
            TSSRENIV1 sett, TSSRENIV2 rep, TSSRENIV3 Srep, TSSRENIV4 Fam, ARTTYPP tipoArt, ARTETAT StatoArt,artcexr codarticolo,
            pkstrucobj.get_desc(0,ART.ArtCINR,''IT'') DESCRIZIONE_ART, AATCATT s,
            vend.ultima_vendita as ultima_vendita , ordinati.ultimo_ordine as ultimo_ordine,
            ordinati.qta_in_ordine qta_in_ordine, ordinati.dta_cons as dta_cons, ricevuti.ultimo_ricevimento as ultimo_ricevimento,
            ultimoinventario as ultimo_inventario
        from artrac art, tsv_strucrel stru, Vend,Ordinati, Ricevuti, artattri,Inventario
        where 1= 1
            and artcexr not in (''#RIF!'')
            and art.artcinr = ordinati.ordcexr (+)
            and art.artcinr = ricevuti.riccexr (+)
            and art.artcinr = vend.vencexr (+)
            and art.artcexr = inventario.codart (+)
            and art.artcexr = stru.TSSRECEXR
            and TSSRENIV1 in (''1'')
            and artcinr = AATCINR
            and AATCCLA =''SARGC''
            and trunc(sysdate) between AATDDEB and AATDFIN
            and ULTIMA_VENDITA < trunc(sysdate -8)
             ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_invtot_fase1;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 7b/23 t_InvendutiTot (Fase2 - Sett.1, senza vendite) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_invtot_fase2') IS NOT NULL DROP TABLE #test_invtot_fase2;
    SELECT * INTO #test_invtot_fase2
    FROM openquery([GC.CEN.TEST],'with Vend as (select distinct arucinr VENCEXR, max(stmdmvt) ultima_vendita
                                from stomvt, ARTUL
                                where stmtmvt = 150
                                    and stmmotf not in (20,520)
                                    and stmcinl = arucinl
                                group by arucinr ),
                    Ordinati as (select distinct arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine, DCDDLIV dta_Cons,
                                        sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
                                from cdedetcde, ARTUL
                                where DCDCINL = arucinl
                                    and dcdetat = 5
                                    and DCDDLIV > =  trunc(sysdate)
                                group by arucinr, DCDDLIV),
                    Ricevuti as ( select distinct arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
                                from stodetre, ARTUL
                                where SDRCINLS = arucinl
                                group by arucinr),
                    Inventario as (select artcexr codart, max(DINDINV) ultimoinventario
                                from artrac a left join invdetinv i on a.artcinr = i.dincinr
                                where 1=1
                                    and DINDINV not in(''2024/03/31'')
                                group by artcexr )
                    select to_char(sysdate,''dd/mm/yyyy'') dtaaggio, ARTDCRE dtacreaz,
                        TSSRENIV1 sett, TSSRENIV2 rep, TSSRENIV3 Srep, TSSRENIV4 Fam, ARTTYPP tipoArt, ARTETAT StatoArt,artcexr codarticolo,
                        pkstrucobj.get_desc(0,ART.ArtCINR,''IT'') DESCRIZIONE_ART,AATCATT s,
                        vend.ultima_vendita as ultima_vendita , ordinati.ultimo_ordine as ultimo_ordine,
                        ordinati.qta_in_ordine qta_in_ordine, ordinati.dta_cons as dta_cons,
                        ricevuti.ultimo_ricevimento as ultimo_ricevimento,
                        ultimoinventario as ultimo_inventario
                    from artrac art, tsv_strucrel stru, Vend,Ordinati, Ricevuti, artattri,Inventario
                    where 1= 1
                        and artcexr not in (''#RIF!'')
                        and art.artcinr = ordinati.ordcexr (+)
                        and art.artcinr = ricevuti.riccexr (+)
                        and art.artcinr = vend.vencexr (+)
                        and art.artcexr = inventario.codart (+)
                        and art.artcexr = stru.TSSRECEXR
                        and TSSRENIV1 in (''1'')
                        and artcinr = AATCINR
                        and AATCCLA =''SARGC''
                        and trunc(sysdate) between AATDDEB and AATDFIN
                        and (ULTIMA_VENDITA) is null
                        and substr(pkstrucobj.get_desc(0,ART.ArtCINR,''IT''),1,4) not in(''EXPO'')');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_invtot_fase2;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 8/23 t_Invendutitot3_4 (Fase1 - Sett.3/4, con vendite) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_invtot34_fase1') IS NOT NULL DROP TABLE #test_invtot34_fase1;
    SELECT * INTO #test_invtot34_fase1
        FROM Openquery([GC.CEN.TEST],'with
        Vend as (select distinct arucinr VENCEXR, max(stmdmvt) ultima_vendita
                  from stomvt, ARTUL
                  where stmtmvt = 150
                     and stmmotf not in (20,520)
                     and stmcinl = arucinl
                  group by arucinr ),
        Ordinati as (select distinct arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine, DCDDLIV dta_Cons,
                         sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
                    from cdedetcde, ARTUL
                    where DCDCINL = arucinl
                        and dcdetat = 5
                        and DCDDLIV > =  trunc(sysdate)
                    group by arucinr, DCDDLIV),
        Ricevuti as ( select distinct arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
                    from stodetre, ARTUL
                    where SDRCINLS = arucinl
                    group by arucinr),
        Inventario as (select artcexr codart, max(DINDINV) ultimoinventario
                from artrac a left join invdetinv i on a.artcinr = i.dincinr
                where 1=1
                and DINDINV not in(''2023/12/31'')
                group by artcexr )
        select to_char(sysdate,''dd/mm/yyyy'') dtaaggio,ARTDCRE dtacreaz,
            TSSRENIV1 sett, TSSRENIV2 rep, TSSRENIV3 Srep, TSSRENIV4 Fam, ARTTYPP tipoArt, ARTETAT StatoArt,artcexr codarticolo,
            pkstrucobj.get_desc(0,ART.ArtCINR,''IT'') DESCRIZIONE_ART, AATCATT s,
            vend.ultima_vendita as ultima_vendita , ordinati.ultimo_ordine as ultimo_ordine,
            ordinati.qta_in_ordine qta_in_ordine, ordinati.dta_cons as dta_cons, ricevuti.ultimo_ricevimento as ultimo_ricevimento,
            ultimoinventario as ultimo_inventario
        from artrac art, tsv_strucrel stru, Vend,Ordinati, Ricevuti, artattri,Inventario
        where 1= 1
            and artcexr not in (''#RIF!'')
            and art.artcinr = ordinati.ordcexr (+)
            and art.artcinr = ricevuti.riccexr (+)
            and art.artcinr = vend.vencexr (+)
            and art.artcexr = inventario.codart (+)
            and art.artcexr = stru.TSSRECEXR
            and TSSRENIV1 in (''3'',''4'')
            and artcinr = AATCINR
            and AATCCLA =''SARGC''
            and trunc(sysdate) between AATDDEB and AATDFIN
            and ULTIMA_VENDITA < trunc(sysdate -18)
             ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_invtot34_fase1;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 8b/23 t_Invendutitot3_4 (Fase2 - Sett.3/4, senza vendite) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_invtot34_fase2') IS NOT NULL DROP TABLE #test_invtot34_fase2;
    SELECT * INTO #test_invtot34_fase2
    FROM openquery([GC.CEN.TEST],'with
        Vend as (select distinct arucinr VENCEXR, max(stmdmvt) ultima_vendita
                    from stomvt, ARTUL
                    where stmtmvt = 150
                        and stmmotf not in (20,520)
                        and stmcinl = arucinl
                    group by arucinr ),
        Ordinati as (select distinct arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine, DCDDLIV dta_Cons,
                            sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
                    from cdedetcde, ARTUL
                    where DCDCINL = arucinl
                        and dcdetat = 5
                        and DCDDLIV > =  trunc(sysdate)
                    group by arucinr, DCDDLIV),
        Ricevuti as ( select distinct arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
                    from stodetre, ARTUL
                    where SDRCINLS = arucinl
                    group by arucinr),
        Inventario as (select artcexr codart, max(DINDINV) ultimoinventario
                    from artrac a left join invdetinv i on a.artcinr = i.dincinr
                    where 1=1
                    and DINDINV not in(''2023/12/31'')
                    group by artcexr )
        select to_char(sysdate,''dd/mm/yyyy'') dtaaggio, ARTDCRE dtacreaz,
            TSSRENIV1 sett, TSSRENIV2 rep, TSSRENIV3 Srep, TSSRENIV4 Fam, ARTTYPP tipoArt, ARTETAT StatoArt,artcexr codarticolo,
            pkstrucobj.get_desc(0,ART.ArtCINR,''IT'') DESCRIZIONE_ART,AATCATT s,
            vend.ultima_vendita as ultima_vendita , ordinati.ultimo_ordine as ultimo_ordine,
            ordinati.qta_in_ordine qta_in_ordine, ordinati.dta_cons as dta_cons,
            ricevuti.ultimo_ricevimento as ultimo_ricevimento,
            ultimoinventario as ultimo_inventario
        from artrac art, tsv_strucrel stru, Vend,Ordinati, Ricevuti, artattri,Inventario
        where 1= 1
            and artcexr not in (''#RIF!'')
            and art.artcinr = ordinati.ordcexr (+)
            and art.artcinr = ricevuti.riccexr (+)
            and art.artcinr = vend.vencexr (+)
            and art.artcexr = inventario.codart (+)
            and art.artcexr = stru.TSSRECEXR
            and TSSRENIV1 in (''3'',''4'')
            and artcinr = AATCINR
            and AATCCLA =''SARGC''
            and trunc(sysdate) between AATDDEB and AATDFIN
            and (ULTIMA_VENDITA) is null
            and substr(pkstrucobj.get_desc(0,ART.ArtCINR,''IT''),1,4) not in(''EXPO'')');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_invtot34_fase2;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 9/23 t_PickingNegativi (linked server GOLDSTK -> GC.STK.TEST) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_picking_negativi') IS NOT NULL DROP TABLE #test_picking_negativi;
    SELECT * INTO #test_picking_negativi
    FROM openquery([GC.STK.TEST],'SELECT
             to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
             ar_donord Deposito,
             ar_cproin Prodotto,
             ar_ilogis Variante,
             max(ar_libpro) Descrizione,
             max(ar_nuvcup) Imballo,
             sum(ul_nqtuvc) qta_pezzi,
             pk_conversion.fc_uvc_to_pcb(ar_donord, ar_cproin, ar_arprom, ar_ilogis, sum(ul_nqtuvc)) qta_colli,
             rp_adrpic indirizzo_picking
        FROM  tb_art, tb_eums, tb_lcums, tb_pick
                WHERE    ar_donord = rp_donord
                AND      ar_cproin = rp_cproin
                AND      ar_arprom = rp_arprom
                AND      ar_ilogis = rp_ilogis
                AND      rp_adrpic = ue_adrums
                AND      ar_donord = ''901''
                AND      ue_usscc  = ul_usscc
                AND      nvl(ue_stapre,0) != 500
                AND      ul_cproin = ar_cproin
                AND      NOT EXISTS (SELECT null FROM goldstk.tb_staums WHERE su_usscc = ue_usscc)
                AND      NOT EXISTS (SELECT 1 FROM tb_emb WHERE NVL(em_cproin,0) = ar_cproin)
                GROUP BY ar_donord, ar_cproin, ar_arprom, ar_ilogis, rp_adrpic
                HAVING   sum(ul_nqtuvc) < 0
                ORDER BY rp_adrpic, ar_donord, ar_cproin
                 ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_picking_negativi;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 10/23 t_Rossetto ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_rossetto') IS NOT NULL DROP TABLE #test_t_rossetto;
    SELECT * INTO #test_t_rossetto
        from openquery([GC.CEN.TEST],'select distinct
        to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
        TSSRENIV1 sett,
        TSSRENIV2 Rep,
        TSSRENIV3 Srep,
        TSSRELIBN3 DescrSrep,
        ARASITE sito,
        pkfoudgene.get_cnuf(0,aracfin) codForn,
        pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn,
        PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
        PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,
        ararefc codArtfo,
        artcexr codArt,
        AATCATT Stato,
        pkstrucobj.get_desc(0,arAcinr,''IT'') descrArt,
        TAPPBRUT PrAcq,
        TAPCTVA Iva,
        ARCTCOD tipoEan,
        ARCIETI EticEan,
        to_number(ARCCODE, ''9999999999999'') Ean,
        ARCCODE EanA,
        ARLCEXVL Vl,
        ALOSMAG cons,
        ''Pezzo'' D1, TSARUUXI pzxcrt,
        ''Collo'' D2, TSARUCXS STRATO,
        ''Strato'' D3 , TSARUSXP PALLET
        from  artrac, tsv_strucrel, artuc, TARPRIX, artcoca, artattri,  artul, artvl, ARTASENT,
        tsv_artulul
        where artcexr = TSSRECEXR
                  and artcinr = aracinr
                  and trunc(sysdate) between ARADDEB  and ARADFIN
                  and ARACCIN = TAPCCIN
                  and pkfoudgene.get_cnuf(0,aracfin) = ''889001''
                  and artcinr = tapcinr
                  and trunc(sysdate) between TAPDDEB and TAPDFIN
                  and artcinr = ARCCINR
                  and trunc(sysdate) between ARCDDEB and ARCDFIN
                  and artcinr  = AATCINR
                  and trunc(sysdate) between AATDDEB and AATDFIN
                  and AATCCLA = ''SARGC''
                  and ARCTCOD not in (''5'')
                  and artcinr = ARUCINR
                  and artcinr =ARLCINR
                  and ARASEQVL = ARLSEQVL
                  and artcinr = ALOCINR (+)
                  and trunc(sysdate) between ALODDEB (+) and ALODFIN (+)
                  and araseqvl = tsaruseqvl
        ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_rossetto;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 11/23 t_OrdiniRossetto ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_ordinirossetto') IS NOT NULL DROP TABLE #test_t_ordinirossetto;
    SELECT * INTO #test_t_ordinirossetto FROM
    openquery ([GC.CEN.TEST], 'select * from SIL_ORDROSSETTO');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_ordinirossetto;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 12/23 v_abbigliamento (SOLO lettura mw_abbigliamento, refresh Oracle NON eseguito di proposito) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_abbig') IS NOT NULL DROP TABLE #test_abbig;
    SELECT * INTO #test_abbig FROM OPENQUERY([GC.CEN.TEST], 'SELECT * FROM mw_abbigliamento');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_abbig;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 13/23 r_PianoPromoFuturo ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_pianopromofuturo') IS NOT NULL DROP TABLE #test_pianopromofuturo;
    SELECT *
        INTO #test_pianopromofuturo
    FROM OPENQUERY([GC.CEN.TEST], '
        WITH EXPOS AS (
            SELECT
                ARTCINR AS PADRE,
                ALLCOEFF AS CONTIENE,
                (SELECT ARUCINR FROM ARTUL WHERE ARUCINL = ALLCINLF) AS FIGLIO,
                ARLSEQVL AS SEQVL_PADRE,
                ALLCINLF AS CINL_PADRE
            FROM
                ARTRAC, ARTVL, ARTULUL
            WHERE
                ARTTYPP = 9
                AND ARTCINR = ARLCINR
                AND ALLSEQVLP = ARLSEQVL
                AND ALLTYPL = 3
        ),
        ORDA AS (
            SELECT
                DCDSITE AS sito,
                PKFOUCCOM.GET_NUMCONTRAT(0, DCDCCIN) AS ccom,
                DCDCEXCDE AS ORDCEXR,
                artcexr AS ordacexr,
                (CASE
                    WHEN dcdetat = 5 THEN dcdcoli
                    ELSE 0
                END) AS qta_ord,
                (CASE
                    WHEN ARTTYPP = 1 THEN ''Collo''
                    WHEN ARTTYPP = 9 THEN ''Expo''
                    ELSE ''altro''
                END) AS Gest,
                DCDDLIV AS Dta_Cons,
                (CASE
                    WHEN ROUND((DCDGRA / DCDUAUVC), 2) < 1 AND ROUND((DCDGRA / DCDUAUVC), 2) > 0 THEN DCDGRA || '' Pezzi''
                    WHEN (DCDGRA / DCDUAUVC) > 0 THEN (DCDGRA / DCDUAUVC) || '' Colli''
                    ELSE NULL
                END) AS omaggio
            FROM
                cdedetcde, artrac
            WHERE
                DCDCEXR = artcexr
                AND dcdetat = 5
                AND PKFOUCCOM.GET_NUMCONTRAT(0, DCDCCIN) NOT IN (''901'')
        ),
        EXPORDA AS (
            SELECT
                DCDSITE AS sito,
                PKFOUCCOM.GET_NUMCONTRAT(0, DCDCCIN) AS ccom,
                DCDCEXCDE AS ORDCEXR,
                ARTTYPP AS tpo,
                artcinr AS expocinr,
                artcexr AS expocexr,
                (CASE
                    WHEN dcdetat = 5 THEN dcdcoli
                    ELSE 0
                END) AS qta_ord,
                (CASE
                    WHEN ARTTYPP = 1 THEN ''Collo''
                    WHEN ARTTYPP = 9 THEN ''Expo''
                    ELSE ''altro''
                END) AS Gest,
                DCDDLIV AS Dta_Cons,
                (CASE
                    WHEN ROUND((DCDGRA / DCDUAUVC), 2) < 1 AND ROUND((DCDGRA / DCDUAUVC), 2) > 0 THEN DCDGRA || '' Pezzi''
                    WHEN (DCDGRA / DCDUAUVC) > 0 THEN (DCDGRA / DCDUAUVC) || '' Colli''
                    ELSE NULL
                END) AS omaggio
            FROM
                cdedetcde, artrac
            WHERE
                DCDCEXR = artcexr
                AND dcdetat = 5
                AND PKFOUCCOM.GET_NUMCONTRAT(0, DCDCCIN) NOT IN (''901'')
                AND ARTTYPP = 9
        )
        SELECT DISTINCT
            TO_CHAR(SYSDATE, ''dd/mm/yyyy'') AS dtaaggio,
            TSARPTPNOPR AS "Cod. Piano Gold",
            OPLCEXOPR AS "Piano",
            TO_CHAR(OPLDDEBV, ''dd/mm/yyyy'') AS "Inizio SellOut",
            TO_CHAR(OPLDFINV, ''dd/mm/yyyy'') AS "Fine SellOut",
            pkfoudgene.get_cnuf(0, TSARPCFIN) AS codForn,
            pkfoudgene.get_descriptionfournisseur(0, TSARPCFIN) AS descForn,
            PKFOUCCOM.GET_NUMCONTRAT(0, TSARPCCIN) AS "Ccom",
            PKFOUCCOM.GET_DESC(0, TSARPCCIN) AS "Descrizione Ccom",
            TSSRENIV1 AS "Sett",
            TSSRENIV2 AS "Rep",
            TSSRENIV3 AS "Srep",
            artcexr AS "Cod.Art.",
            TSARPDESC AS "Descrizione Articolo",
            ROUND(TSARPPRZOFF, 2) AS "Prezzo Promo",
            TO_CHAR(TSARPDINISELLIN, ''dd/mm/yyyy'') AS "Inizio SellIn",
            TO_CHAR(TSARPDFINESELLIN, ''dd/mm/yyyy'') AS "Fine SellIn",
            PKARTRAC.GET_ARTCEXR(0, PADRE) AS "Cod.Art.Expo",
            PKSTRUCOBJ.GET_DESC(0, PADRE, ''IT'') AS "Descrizione Expo",
            CONTIENE AS "Pz Contenuti",
            PKARTRAC.GET_ARTCEXR(0, FIGLIO) AS "Cod.Art.Componente",
            PKSTRUCOBJ.GET_DESC(0, FIGLIO, ''IT'') AS "Descr. Componente",
            (CASE
                WHEN orda.gest = ''Collo'' AND exporda.gest IS NOT NULL AND orda.ordcexr = exporda.ordcexr AND orda.omaggio IS NOT NULL
                    THEN '' EXPO - COLLI - OMAGGI''
                WHEN orda.gest = ''Collo'' AND exporda.gest IS NOT NULL AND orda.ordcexr = exporda.ordcexr AND orda.omaggio IS NULL
                    THEN '' EXPO - COLLI ''
                WHEN orda.gest = ''Collo'' AND orda.omaggio IS NOT NULL
                    THEN '' COLLI + OMAGGI''
                WHEN orda.gest = ''Collo'' AND orda.omaggio IS NULL
                    THEN '' COLLI ''
                WHEN exporda.gest = ''Expo'' AND exporda.gest IS NOT NULL AND orda.gest IS NULL
                    THEN ''EXPO''
                ELSE ''-''
            END) AS "Ordine in Corso",
            (CASE
                WHEN orda.gest = ''Collo'' AND orda.gest IS NOT NULL
                    THEN TO_CHAR(orda.Dta_Cons, ''DD/MM/RRRR'')
                WHEN exporda.gest = ''Expo'' AND exporda.gest IS NOT NULL
                    THEN TO_CHAR(exporda.Dta_Cons, ''DD/MM/RRRR'')
                ELSE ''-''
            END) AS "Data di Consegna"
        FROM
            tst_pma_articolo, oprplan, tsv_strucrel, artuv, artrac, expos, orda, exporda
        WHERE
            TSARPTPNOPR = oplnopr
            AND (OPLDDEBV >= TRUNC(SYSDATE) OR OPLDDEBV IS NULL)
            AND TSARPCINV = ARVCINV
            AND arvcinr = artcinr
            AND artcinr = TSSRECINR
            AND ARTCINR = FIGLIO(+)
            AND artcexr = ordacexr(+)
            AND PKARTRAC.GET_ARTCEXR(0, PADRE) = expocexr(+)
        ORDER BY
            artcexr
    ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_pianopromofuturo;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 14/23 t_AnagArticoli ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_anagarticoli') IS NOT NULL DROP TABLE #test_t_anagarticoli;
    SELECT * INTO #test_t_anagarticoli FROM OPENQUERY([GC.CEN.TEST], 'select * from sil_anagarticoli');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_anagarticoli;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 15/23 t_Buyerfo ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_buyerfo') IS NOT NULL DROP TABLE #test_t_buyerfo;
    SELECT * INTO #test_t_buyerfo FROM OPENQUERY([GC.CEN.TEST],'select distinct to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
                                                     substr(sapcexap,-2) cdbuyer,
                                                     sapcexap cdsett ,
                                                     trim(substr(saplibl,1,16)) descrizione,
                                                     fccnum ccom,
                                                     fcclib descrCcom
                                                     from secappro, liensecappro, fouccom
                                                        where liacinap    = sapcinap
                                                           and  fccccin = liaccin
                                                        and trunc(sysdate) between FCCDDEB and     FCCDFIN
                                                        and substr(fcclib,1,1) not in (''*'')');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_buyerfo;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 16/23 t_ExpoArt ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_expoart') IS NOT NULL DROP TABLE #test_t_expoart;
    SELECT *
     INTO #test_t_expoart
    from openquery([GC.CEN.TEST],'WITH EXPOS AS (
        select ARTCINR PADRE, ALLCOEFF CONTIENE, (SELECT ARUCINR FROM ARTUL WHERE ARUCINL = ALLCINLF) FIGLIO, ARLSEQVL SEQVL_PADRE, ALLCINLF CINL_PADRE
          from ARTRAC, ARTVL, ARTULUL
         WHERE ARTTYPP = 9
           AND ARTCINR = ARLCINR
           AND ALLSEQVLP = ARLSEQVL
           AND ALLTYPL = 3),
    Ordinati as (
    select distinct /*+ materialize*/
           arucinr ORDCEXR, max(DCDDCOM) ultimo_Ordine,  sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
      from cdedetcde, ARTUL
     where DCDCINL = arucinl
       group by arucinr),
    Ricevuti as (
    select distinct /*+ materialize*/
           arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento
      FROM STODETRE, ARTUL
     WHERE SDRCINLS = ARUCINL
     group by arucinr)
    SELECT distinct
           to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
           ararefc codArtfo,
           PKARTRAC.GET_ARTCEXR(0,PADRE) CodArtExpo,
           PKSTRUCOBJ.GET_DESC(0,PADRE,''IT'') DescrizioneExpo,
           AATCATT StatoE,
           CONTIENE,
            TO_NUMBER(PKARTRAC.GET_ARTCEXR(0,FIGLIO),9999999) codArtl,
           PKSTRUCOBJ.GET_DESC(0,FIGLIO,''IT'') descrart,
           TSSRENIV1 Settore,
           TSSRENIV2 Reparto,
           TSSRELIBN2 DescRep,
           TSSRENIV3 SOTTOREPARTO,
           TSSRELIBN3 DESCSREP,
           ARCCODE EAN,
           ACUCODE ITF14,
           NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 10001, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, PADRE, SEQVL_PADRE), TRUNC (SYSDATE)), 0) GIACENZA_PDV,
           NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 901, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, PADRE, SEQVL_PADRE), TRUNC (SYSDATE)), 0)/PKARTSTOCK.RECUPCOEFFUVC(1, CINL_PADRE) GIACENZA_DEPOSITO,
           TO_CHAR(ULTIMO_ORDINE,''dd/mm/yyyy'') ULTIMO_ORDINE,
           qta_in_ordine,
           TO_CHAR(ULTIMO_RICEVIMENTO, ''dd/mm/yyyy'') ULTIMO_RICEVIMENTO,
           PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
           PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom
      FROM EXPOS, TSV_STRUCREL, ARTCOCA, ARTCOUL, ricevuti, ordinati, artattri, artuc
     WHERE TSSRECINR = PADRE
       AND ARCCINR = PADRE
       and aatcinr = arccinr
       and trunc(sysdate) between AATDDEB and AATDFIN
       and AATCCLA = ''SARGC''
       and ARCIETI = 1
       AND ACUCINR(+) = PADRE
       AND ARACINR = arccinr
       and trunc(sysdate) between ARADDEB and ARADFIN
       AND PADRE = ORDCEXR (+)
       and PADRE = RICCEXR (+)');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_expoart;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 17/23 t_MasterAssortimenti ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_masterassortimenti') IS NOT NULL DROP TABLE #test_t_masterassortimenti;
    SELECT * INTO #test_t_masterassortimenti FROM OPENQUERY([GC.CEN.TEST],'select distinct
        to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
        ARASITE sito,TSSRENIV1 sett,TSSRENIV2 Rep,TSSRELIBN2 DescrRep,TSSRENIV3 Srep,TSSRELIBN3 DescrSrep,TSSRENIV4 fam,TSSRELIBN4 DescrFam,
        pkfoudgene.get_cnuf(0,aracfin) codForn,pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn,PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
        PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,TSK_FLODASH.GET_LINEA_PRODOTTO(ARTCEXR,TRUNC(SYSDATE)) LINEA_PRODOTTO,
        TSFLLDES Descr_Linea,
        nvl(TSK_FLODASH.GET_TIPO_RIORDINO(ARTCEXR,TRUNC(SYSDATE)), '''') TIPO_RIORDINO,
        ararefc codArtfo,artcexr codArt,AATCATT Stato,pkstrucobj.get_desc(0,arAcinr,''IT'') descrArt,
        TAPPBRUT PrAcq, COSTOCOMM costoCom, NETTO CostoNetto, NETTONETTO CostoNetNet, TAPCTVA Iva,
        ARCTCOD tipoEan, ARCCODE Ean,arccode EanA, aratfou FornPrinc, ARTTYPP TipoArt,
        PKPRIXVENTE.GET_PRIX_VENTE(0,ARVCINV,10001,3,TRUNC(SYSDATE)) prz_vend
        from artrac, tsv_strucrel, artuc, TARPRIX, artcoca, artattri,  artul, artvl, ARTASENT, SIL_przacq, artuv , tst_forlin_ext
        where artcexr = TSSRECEXR and artcinr = aracinr and trunc(sysdate) between ARADDEB  and ARADFIN
        and ARACCIN = TAPCCIN and artcinr = tapcinr and trunc(sysdate) between TAPDDEB and TAPDFIN
        and artcinr = ARCCINR
        and trunc(sysdate) between ARCDDEB and ARCDFIN
        and artcinr  = AATCINR
        and trunc(sysdate) between AATDDEB and AATDFIN
        and AATCCLA = ''SARGC''
        and ARCTCOD not in (''5'')
        and artcinr = ARUCINR
        and artcinr =ARLCINR
        and ARASEQVL = ARLSEQVL
        and artcinr = ALOCINR (+)
        and trunc(sysdate) between ALODDEB (+) and ALODFIN (+)
        and TSK_FLODASH.GET_LINEA_PRODOTTO(ARTCEXR,TRUNC(SYSDATE)) = TSFLLCOD
        and ARCIETI = 1
        and artcexr  = CODART (+)
        and ARVCINR = artcinr');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_masterassortimenti;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 18/23 t_MasterDataOfferte ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_masterdataofferte') IS NOT NULL DROP TABLE #test_t_masterdataofferte;
    SELECT *
     INTO #test_t_masterdataofferte
    from openquery([GC.CEN.TEST],'with Venduti as (select distinct  arucinr VENCEXR, max(stmdmvt) ultima_vendita
      from stomvt, ARTUL where stmtmvt = 150    and stmmotf not in (20,520)   and stmcinl = arucinl
       group by arucinr), Resi as (select distinct /*+ materialize*/
      arucinr RESCEXR, SUM(STMVAL) Qta_reso, sum(STMVPV) Val_reso
      from stomvt, ARTUL where stmtmvt = 113    and stmcinl = arucinl   and stmdmvt = trunc(sysdate - 1)   group by arucinr),
    Ordinati as (select distinct  arucinr ORDCEXR, max(DCDDLIV) ultimo_Ordine,  sum(case when dcdetat = 5 then dcdqtec else 0 end) qta_in_ordine
      from cdedetcde, ARTUL where DCDCINL = arucinl and dcdetat = 5   group by arucinr),
    Ricevuti as (select distinct arucinr RICCEXR, max(SDRSDRC) ultimo_Ricevimento  from stodetre, ARTUL
     where SDRCINLS = arucinl   group by arucinr) select to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
      TSSRENIV1 Settore,  TSSRENIV2 Reparto,  TSSRELIBN2 DescRep,  TSSRENIV3 SottoReparto,  TSSRELIBN3 DescSRep,
      TSSRENIV4 Famiglia,  TSSRELIBN4 DescFam,  pkfoudgene.get_cnuf(0,aracfin) codForn,
      pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn, TO_NUMBER(PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN), 9999999) CCom,
      PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,  ararefc codArtfo, ARVCEXR codArt, AATCATT stato,pkstrucobj.get_desc(0,arvcinr,''IT'') descrArt,
      arcieti Eanprinc,  arccode EAN, PKARTUL.GETLIBLTYPEUL(1, ARACINL, ''IT'') Gest,
      PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) PzXCart, PKPRIXVENTE.GET_PRIX_VENTE(0,ARVCINV,10001,3,TRUNC(SYSDATE)) prz_vend,
      NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 10001, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (sysdate+1)), 0) GIACENZA_PDV,
      NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1, 901, PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARACINR, ARASEQVL), TRUNC (SYSDATE+1)), 0)/PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) GIACENZA_DEPOSITO,
      qta_in_ordine,   to_char(ultimo_Ordine,''dd/mm/yyyy'') ultimo_Ordine,
      to_char(ULTIMA_VENDITA,''dd/mm/yyyy'') ultima_vendita,
      to_char(ultimo_Ricevimento, ''dd/mm/yyyy'') ultimo_ricevimento,
      Qta_reso,  Val_reso,  (select listagg(OPLCEXOPR,'', '') within group (order by 1)
      from tst_pma_articolo,oprplan  where TSARPTPNOPR = oplnopr  and TSARPCINV = arvcinv  and trunc(sysdate) between OPLDDEBV and OPLDFINV) CodPromo,
      cartpall
      from Venduti, ordinati, Ricevuti, Resi, artattri,
      artsite, artuv, tsv_strucrel, artuc , artcoca, TSV_CARTONI_PALLET
        where aracinr = arvcinr (+)  and pkfoudgene.get_foutype(0,aracfin) <> 3
       and aratfou = 1  and arvcinr = VENCEXR (+)
       and arvcinr = ORDCEXR (+)  and arvcinr = RICCEXR (+)
       and arvcinr = RESCEXR (+)  and arvcinv = sitcinv
       and arvcinr = TSSRECINR  and SITFSUP = 0
       and AATCINR = aracinr and ARASEQVL = SEQVL (+)
       and AATCCLA = ''SARGC''
       and trunc(sysdate) between AATDDEB and AATDFIN
       and AATCATT <> ''A''  and aracinr = arccinr and trunc(sysdate) between arcddeb and arcdfin
       and arctcod <> 5   and arctcod <> 9
    ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_masterdataofferte;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 19/23 t_MasterStock (linked server GOLDSTK -> GC.STK.TEST) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_masterstock') IS NOT NULL DROP TABLE #test_t_masterstock;
    SELECT *
    into #test_t_masterstock
    from openquery([GC.STK.TEST],' select distinct
                    to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
                    AR_FOURN CodFo,
                    AR_NRSFOU RagioneSociale,
                    to_number(ar_cproin) codArticolo,
                    ar_ilogis VL,
                    ar_libpro DescrizioneArticolo,
                    sum(colli) GiacenzaDeposito,
                    RP_ADRPIC indpick
    from (SELECT distinct ar_cproin, ar_arprom, ar_ilogis, ar_libpro, AR_FOURN,  AR_NRSFOU,
             SUM (NVL (rp_nqtuvc, 0)) Pezzi,
             SUM (round(NVL (rp_nqtuvc/AR_NUVSPC, 0),0)) colli,
             SUM (NVL (rp_pdsnet, 0)) Peso
             FROM v_pick_3, tb_art
            WHERE     rp_arprom = ar_arprom
             AND rp_ilogis = ar_ilogis
             AND rp_donord = ar_donord
             AND rp_cproin = ar_cproin
    GROUP BY ar_cproin, ar_arprom, ar_ilogis, ar_libpro, ar_nuvcup, AR_FOURN, AR_NRSFOU
    union SELECT distinct ar_cproin, ar_arprom, ar_ilogis, ar_libpro, AR_FOURN, AR_NRSFOU,
           NVL (SUM (NVL (ul_nqtuvc, 0)), 0) pezzi,
           NVL (SUM (NVL (ul_nqtuvc/AR_NUVSPC, 0)), 0) colli,
           NVL (SUM (NVL (ul_pdsnet, 0)), 0)
      FROM tb_art,  tb_eums, tb_cums, tb_lcums
    WHERE     ar_cproin = ul_cproin
           AND ar_arprom = ul_arprom
           AND ar_ilogis = ul_ilogis
           AND ar_donord = ul_donord
           AND UC_USSCC = UE_USSCC
           AND UL_USSCC = UC_USSCC
           AND UL_CSSCC = UC_CSSCC
            AND NVL (ue_stapre, ''000'') NOT IN (''500'')
           AND ul_indcom = ''0''
           AND ue_codtsu = ''1''
           AND NVL (ue_indfic, ''1'') != ''0''
           AND NOT EXISTS (SELECT 1 FROM tb_lotet WHERE le_usscc = ue_usscc)
           GROUP BY ar_cproin, ar_arprom, ar_ilogis, ar_libpro, ar_nuvcup , AR_FOURN, AR_NRSFOU), tb_pick
     where
     ar_cproin = RP_CPROIN
     and ar_ilogis = RP_ILOGIS
    GROUP BY ar_cproin, ar_arprom, ar_ilogis, ar_libpro, AR_FOURN, AR_NRSFOU, RP_ADRPIC');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_masterstock;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 20/23 t_OrdiniGenerale ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_ordinigenerale') IS NOT NULL DROP TABLE #test_t_ordinigenerale;
    SELECT * INTO #test_t_ordinigenerale from openquery([GC.CEN.TEST],'select * from (select distinct
           to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
           DCDSITE sito,
           to_char(DCDDCOM,''dd/mm/yyyy'') data_Ordine,
           to_char(DCDDLIV,''dd/mm/yyyy'')  data_consegna,
           arucinr ORDCEXR,
           DCDCEXCDE,
           ecdetat Stato_testataOrdine,
           dcdetat stato,
           TPARLIBL trad,
           DCDCEXR codArt,
           pkstrucobj.get_desc(0,arvcinr,''IT'') descrArt,
           dcdqtec / PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) qtains,
           DCDCOLI colliOrd,
           PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) PzXuL,
           arutypul ||'' - ''||PKPARPOSTES.GET_POSTLIBL(0,0,731,arutypul, ''IT'') Gestione,
           dcdqtec PZ_ord,
           DCDRAL  / PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL) ColliNonConse,
           round(NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1,901,dcdcinl, TRUNC (SYSDATE+1)), 0) / PKARTSTOCK.RECUPCOEFFUVC(1, ARACINL),2) GIACENZA_DEPOSITO,
           NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1,10001,dcdcinl, TRUNC (SYSDATE+1)), 0) GIACENZA_PDV,
           count(*) over (partition by dcdcexcde, dcdcexr),
           aracfin,
           pkfoudgene.get_foutype(0, aracfin) tipoFo,
           pkfoudgene.get_cnuf(0,aracfin) codForn,
           pkfoudgene.get_descriptionfournisseur(0,aracfin) descForn,
           PKFOUCCOM.GET_NUMCONTRAT(0,ARACCIN) CCom,
           PKFOUCCOM.GET_DESC(0,ARACCIN) descrCcom,
           ARACEXVL VL
     from cdeentcde,cdedetcde, ARTUL, ARTUV, ARTUC, TRA_PARPOSTES, ARTvl
         where  1=1
         and ecdcincde = dcdcincde
         and ARACINR = arvcinr
         and DCDCINA = arucinl
         and ARVCINR = arucinr
         and arlcinr = arvcinr
         and aracfin = dcdcfin
         and TPARTABL = 502
         and LANGUE = ''IT''
         and TPARPOST = DCDETAT
         and TPARCMAG = 0
         and DCDDCOM between trunc(sysdate-10)  and trunc(sysdate+20)
         and dcddcom between araddeb and aradfin
         group by
             DCDSITE, DCDDCOM, aracinr, arucinr,  DCDDLIV, DCDCEXCDE,  DCDCEXR,  arvcinr, ARACCIN, ARACINL, arutypul,  dcdcinl, DCDRAL, DCDCOLI,
             ecdetat,dcdetat, dcdqtec, dcdqtec, TPARLIBL, DCDDCOM, ARLSEQVL, aracfin, ARACEXVL)');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_ordinigenerale;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 21/23 t_PromoFuture ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_promofuture') IS NOT NULL DROP TABLE #test_t_promofuture;
    SELECT *
     into #test_t_promofuture
     FROM OPENQUERY([GC.CEN.TEST],'
    select
            to_char(sysdate,''dd/mm/yyyy'') dtaaggio,
           OPLCEXOPR,
           to_char(OPLDDEBV,''dd/mm/yyyy'') dtaIni,
           to_char(OPLDFINV,''dd/mm/yyyy'' ) dtafine,
           arvcexr,
           pkstrucobj.get_desc(0,arvcinr, ''IT''),
           arccode,
           NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1,10001,PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARVCINR, ARLSEQVL), TRUNC (sysdate+1)), 0) GIACENZA_PDV,
           NVL (PKSTOCK.GETSTOCKENQTEVALADATE (1,901,PKARTSTOCK.RECUPCINLUVCPARCINRETSEQVL (1, ARVCINR, ARLSEQVL), TRUNC (SYSDATE+1)), 0) GIACENZA_DEPOSITO,
           TSARPPRZOFF prz_off,
           TSARPTPNOPR CodPiano
      from tst_pma_articolo, oprplan, artuv, artcoca, artvl
     where TSARPTPNOPR = oplnopr
       and TSARPCINV = arvcinv
       and arccinr  = arvcinr
       and arlcinr = arvcinr
        AND OPLDFINV >= TRUNC(SYSDATE-30)
       ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_promofuture;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 22/23 t_przacq (query principale) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_przacq') IS NOT NULL DROP TABLE #test_t_przacq;
    select *
    into #test_t_przacq
    from
    openquery([GC.CEN.TEST], 'select * from sil_przacq ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_przacq;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE: ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 22b/23 t_przacq_dash (ATTENZIONE: usa DB link Oracle interno DASHGCIDAC - vedi note in testa allo script) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_przacq_dash') IS NOT NULL DROP TABLE #test_t_przacq_dash;
    select * into #test_t_przacq_dash from openquery([GC.CEN.TEST],'select TSPAFCOD ccom , TSPAACOD codart, TSPAVL vl , TSPALISTINO prlist ,TSARCIVA iva
    from DASHGCIDAC.tst_przacq_ext, tst_art_ext
    where 1=1
    and TSPAACOD=TSARACOD
    and TSPAFCOD = ''807764''');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_przacq_dash;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE (probabile causa: DB link DASHGCIDAC assente su GC.CEN.TEST): ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== 23/23 t_stockpick (linked server GOLDSTK -> GC.STK.TEST; ATTENZIONE: usa DB link Oracle interno DBL_CENTRAL5.GROSCIDAC.local - vedi note in testa allo script) ===';
BEGIN TRY
    IF OBJECT_ID('tempdb..#test_t_stockpick') IS NOT NULL DROP TABLE #test_t_stockpick;
    select *
    into #test_t_stockpick
    from
    openquery([GC.STK.TEST],'select distinct  RP_ZONE Mag, RP_ADRPIC pickStatico, RP_ADRDYN pickDin ,ar_cproin codArt,  ar_libpro Descr,
        RP_SECUPI Soglia, RP_QTESAT QtaSat, to_char(RP_DATINV,''dd/mm/yyyy'') DataInv, AATCCLA CodAttri,
        AATCATT Stato
        from tb_art, tb_pick, artattri@DBL_CENTRAL5.GROSCIDAC.local, ARTrac@DBL_CENTRAL5.GROSCIDAC.local
        where
        AATCINR = artcinr
        and trunc(sysdate) between AATDDEB and AATDFIN
        and AATCCLA =''SARGC''
        and artcexr = ar_cproin
        and RP_CPROIN = ar_cproin ');
    DECLARE @cnt INT; SELECT @cnt = COUNT(*) FROM #test_t_stockpick;
    PRINT 'OK - righe: ' + CAST(@cnt AS VARCHAR(20));
END TRY
BEGIN CATCH
    PRINT 'ERRORE (probabile causa: DB link DBL_CENTRAL5.GROSCIDAC.local assente su GC.STK.TEST): ' + ERROR_MESSAGE();
END CATCH
GO

PRINT '=== FINE TEST - controlla sopra tutti gli OK/ERRORE ===';
