<?xml version="1.0" encoding="UTF-8"?>
<!--
  chookaszian.sch
  ================================================================
  ISO Schematron rules that enforce the project-specific TEI
  constraints documented in odd/chookaszian.odd. Applied at runtime
  by pipeline/validate_tei.py via lxml.isoschematron.

  Severity discipline:

    role="error"    : blocks the validation gate (exit non-zero)
    role="warning"  : reported but does not fail validation

  Warnings are used for controlled vocabularies (xml:lang, @type)
  so Phase-2 encoding work and Phase-3 enrichment can iterate
  without the CI gate rejecting every new language tag or type
  value on first sight.

  Errors are reserved for invariants the corpus already satisfies:
  teiHeader completeness, xml:id on standOff persons/msDescs,
  and @n on pb once page breaks are encoded.
-->
<sch:schema xmlns:sch="http://purl.oclc.org/dsdl/schematron"
            queryBinding="xslt1">

  <sch:ns prefix="tei" uri="http://www.tei-c.org/ns/1.0"/>
  <sch:ns prefix="xml" uri="http://www.w3.org/XML/1998/namespace"/>

  <!-- ============================================================
       Pattern: header-completeness
       Every TEI article must have a non-empty title, publicationStmt,
       and sourceDesc inside teiHeader/fileDesc.
       ============================================================ -->
  <sch:pattern id="header-completeness">
    <sch:title>teiHeader completeness</sch:title>

    <sch:rule context="tei:TEI/tei:teiHeader/tei:fileDesc">
      <sch:assert test="tei:titleStmt/tei:title[normalize-space(.) != '']"
                  role="error"
                  id="header-title-nonempty">
        Every article's teiHeader/fileDesc/titleStmt must contain a
        non-empty title child (Phase-1 acceptance).
      </sch:assert>

      <sch:assert test="tei:publicationStmt[normalize-space(.) != '']"
                  role="error"
                  id="header-publicationStmt-nonempty">
        Every article's teiHeader/fileDesc must contain a non-empty
        publicationStmt (records publication provenance).
      </sch:assert>

      <sch:assert test="tei:sourceDesc[normalize-space(.) != '']"
                  role="error"
                  id="header-sourceDesc-nonempty">
        Every article's teiHeader/fileDesc must contain a non-empty
        sourceDesc (records extraction source).
      </sch:assert>
    </sch:rule>
  </sch:pattern>

  <!-- ============================================================
       Pattern: standoff-xmlid
       Every person or msDesc inside standOff must carry xml:id so
       downstream RAG / entity panel can reference it stably.
       ============================================================ -->
  <sch:pattern id="standoff-xmlid">
    <sch:title>standOff registers require xml:id</sch:title>

    <sch:rule context="tei:standOff//tei:person">
      <sch:assert test="@xml:id"
                  role="error"
                  id="standoff-person-xmlid">
        Every &lt;person&gt; inside &lt;standOff&gt; must carry @xml:id
        for downstream cross-reference.
      </sch:assert>
    </sch:rule>

    <sch:rule context="tei:standOff//tei:msDesc">
      <sch:assert test="@xml:id"
                  role="error"
                  id="standoff-msDesc-xmlid">
        Every &lt;msDesc&gt; inside &lt;standOff&gt; must carry @xml:id
        for downstream cross-reference and shelfmark linking.
      </sch:assert>
    </sch:rule>
  </sch:pattern>

  <!-- ============================================================
       Pattern: pb-has-n
       If any pb element exists it must carry @n (page number).
       No pb elements exist in the current corpus - Phase-2 gap.
       ============================================================ -->
  <sch:pattern id="pb-has-n">
    <sch:title>pb elements must carry @n</sch:title>

    <sch:rule context="tei:pb">
      <sch:assert test="@n"
                  role="error"
                  id="pb-n-required">
        &lt;pb/&gt; must carry @n (original page number). See CLAUDE.md
        Phase-2 acceptance criterion.
      </sch:assert>
    </sch:rule>
  </sch:pattern>

  <!-- ============================================================
       Pattern: lang-vocab
       xml:lang values must come from the project vocabulary. Warns
       (not errors) so Phase-2 encoding can add new tags iteratively.
       ============================================================ -->
  <sch:pattern id="lang-vocab">
    <sch:title>xml:lang controlled vocabulary</sch:title>

    <sch:rule context="*[@xml:lang]">
      <sch:let name="v" value="string(@xml:lang)"/>
      <sch:report test="not($v = 'hy'
                       or $v = 'hy-arevela-classic'
                       or $v = 'xcl'
                       or $v = 'xcl-Latn'
                       or $v = 'ru'
                       or $v = 'fr'
                       or $v = 'en')"
                  role="warning"
                  id="lang-vocab-unknown">
        xml:lang="<sch:value-of select="$v"/>" is not in the project
        vocabulary (hy, hy-arevela-classic, xcl, xcl-Latn, ru, fr, en).
        If this is intentional, add it to odd/chookaszian.odd.
      </sch:report>
    </sch:rule>
  </sch:pattern>

  <!-- ============================================================
       Pattern: type-vocab
       @type values must come from the project whitelist. Warns
       (not errors) so novel @type usage can be reviewed.
       Whitelist (discovered from tei/ + tei_enriched/ 2026-07):
         source_pages, manuscript-refs
       Plus TEI-standard idioms we tolerate silently:
         div/@type, note/@type when non-project (footnote, etc.)
       For now we scope the check to <note> and <listBibl>, the only
       elements where enrichment writes project-specific @type today.
       Extend as new project types appear.
       ============================================================ -->
  <sch:pattern id="type-vocab">
    <sch:title>project @type controlled vocabulary</sch:title>

    <sch:rule context="tei:note[@type]">
      <sch:let name="v" value="string(@type)"/>
      <sch:report test="not($v = 'source_pages')"
                  role="warning"
                  id="type-vocab-note-unknown">
        note[@type="<sch:value-of select="$v"/>"] is not in the project
        whitelist for note (source_pages). If intentional, add it to
        odd/chookaszian.odd.
      </sch:report>
    </sch:rule>

    <sch:rule context="tei:listBibl[@type]">
      <sch:let name="v" value="string(@type)"/>
      <sch:report test="not($v = 'manuscript-refs')"
                  role="warning"
                  id="type-vocab-listBibl-unknown">
        listBibl[@type="<sch:value-of select="$v"/>"] is not in the
        project whitelist for listBibl (manuscript-refs). If intentional,
        add it to odd/chookaszian.odd.
      </sch:report>
    </sch:rule>
  </sch:pattern>

</sch:schema>
