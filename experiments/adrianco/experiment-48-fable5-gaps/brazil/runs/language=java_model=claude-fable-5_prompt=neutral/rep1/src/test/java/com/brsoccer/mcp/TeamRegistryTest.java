package com.brsoccer.mcp;

import com.brsoccer.mcp.data.TeamRegistry;
import org.junit.jupiter.api.Test;

import static com.brsoccer.mcp.data.TeamRegistry.canonicalKey;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Team-name normalization across the naming conventions used by the different files. */
class TeamRegistryTest {

    @Test
    void stateSuffixVariantsCollapse() {
        assertEquals(canonicalKey("Flamengo"), canonicalKey("Flamengo-RJ"));
        assertEquals(canonicalKey("Flamengo"), canonicalKey("Flamengo - RJ"));
        assertEquals(canonicalKey("Flamengo"), canonicalKey("Flamengo RJ"));
        assertEquals(canonicalKey("Palmeiras"), canonicalKey("Palmeiras-SP"));
        assertEquals(canonicalKey("São Paulo"), canonicalKey("Sao Paulo-SP"));
        assertEquals(canonicalKey("Grêmio"), canonicalKey("Gremio-RS"));
        assertEquals(canonicalKey("Avaí"), canonicalKey("Avai-SC"));
    }

    @Test
    void accentsAreIgnored() {
        assertEquals(canonicalKey("Sao Paulo"), canonicalKey("São Paulo"));
        assertEquals(canonicalKey("Gremio"), canonicalKey("Grêmio"));
        assertEquals(canonicalKey("Ceara"), canonicalKey("Ceará - CE"));
        assertEquals(canonicalKey("Criciuma"), canonicalKey("Criciúma - SC"));
    }

    @Test
    void ambiguousBaseNamesKeepTheirState() {
        // Atlético Mineiro vs Athletico Paranaense vs Atlético Goianiense must stay distinct
        String mg = canonicalKey("Atlético-MG");
        String pr = canonicalKey("Athletico-PR");
        String go = canonicalKey("Atlético-GO");
        assertNotEquals(mg, pr);
        assertNotEquals(mg, go);
        assertEquals(mg, canonicalKey("Atletico Mineiro"));
        assertEquals(mg, canonicalKey("Atlético Mineiro - MG"));
        assertEquals(pr, canonicalKey("Atletico Paranaense"));
        assertEquals(pr, canonicalKey("Atlético - PR"));
        assertEquals(pr, canonicalKey("Athletico Paranaense - PR"));
        assertNotEquals(canonicalKey("Botafogo-RJ"), canonicalKey("Botafogo - PB"));
        assertNotEquals(canonicalKey("Santos - SP"), canonicalKey("Santos - AP"));
    }

    @Test
    void plainAmbiguousNameResolvesToFamousClub() {
        assertEquals(canonicalKey("Flamengo-RJ"), canonicalKey("Flamengo"));
        assertEquals(canonicalKey("Santos-SP"), canonicalKey("Santos"));
        assertEquals(canonicalKey("Internacional - RS"), canonicalKey("Internacional"));
        assertEquals(canonicalKey("Vitória - BA"), canonicalKey("Vitoria"));
    }

    @Test
    void aliasesUnifyRenamedAndLongFormNames() {
        assertEquals(canonicalKey("Vasco"), canonicalKey("Vasco da Gama - RJ"));
        assertEquals(canonicalKey("Vasco"), canonicalKey("Vasco Da Gama RJ"));
        assertEquals(canonicalKey("Bragantino"), canonicalKey("Red Bull Bragantino"));
        assertEquals(canonicalKey("Sport"), canonicalKey("Sport Recife"));
        assertEquals(canonicalKey("Sport"), canonicalKey("Sport-PE"));
        assertEquals(canonicalKey("CSA"), canonicalKey("C.s.a. - AL"));
        assertEquals(canonicalKey("CRB"), canonicalKey("C. R. B. - AL"));
        assertEquals(canonicalKey("Fortaleza"), canonicalKey("Fortaleza EC"));
        assertEquals(canonicalKey("Fortaleza"), canonicalKey("Fortaleza - CE"));
    }

    @Test
    void corporateNoiseTokensAreDropped() {
        assertEquals(canonicalKey("Bahia"), canonicalKey("EC Bahia"));
        assertEquals(canonicalKey("Vitoria - BA"), canonicalKey("EC Vitoria"));
        assertEquals(canonicalKey("Serra"), canonicalKey("Serra F. C. - ES"));
    }

    @Test
    void longParentheticalsAreIgnored() {
        assertEquals(canonicalKey("Boavista - RJ"),
            canonicalKey("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ"));
    }

    @Test
    void internationalTeamsKeepCountryMarker() {
        assertEquals(canonicalKey("Nacional (URU)"), canonicalKey("Nacional-URU"));
        assertNotEquals(canonicalKey("Nacional (URU)"), canonicalKey("Nacional - AM"));
        assertNotEquals(canonicalKey("Peñarol"), canonicalKey("Penarol - AM"));
        assertEquals(canonicalKey("Guaraní (PAR)"), canonicalKey("Guaraní-PAR"));
        assertNotEquals(canonicalKey("Guaraní (PAR)"), canonicalKey("Guarani - SP"));
    }

    @Test
    void queryPrefixMatching() {
        assertTrue(TeamRegistry.keyMatches(canonicalKey("Nacional - AM"), canonicalKey("Nacional")));
        assertTrue(TeamRegistry.keyMatches(canonicalKey("Flamengo-RJ"), canonicalKey("Flamengo")));
    }
}
