Describe "Get-RedactedMessage" {
    BeforeAll {
        $scriptContent = Get-Content -Path "tools/export_ha_nuisance_evidence.ps1" -Raw
        $ast = [System.Management.Automation.Language.Parser]::ParseInput($scriptContent, [ref]$null, [ref]$null)
        $functionAst = $ast.FindAll({$args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $true) | Where-Object { $_.Name -eq 'Get-RedactedMessage' }
        Invoke-Expression $functionAst.Extent.Text
    }

    It "redacts an access token from a message" {
        Get-RedactedMessage -Message "Bearer abc123 failed" -Token "abc123" |
            Should -Be "Bearer [REDACTED_TOKEN] failed"
    }

    It "redacts every occurrence of the token" {
        Get-RedactedMessage -Message "abc123 then abc123" -Token "abc123" |
            Should -Be "[REDACTED_TOKEN] then [REDACTED_TOKEN]"
    }

    It "returns the original message when token is empty" {
        Get-RedactedMessage -Message "nothing changes" -Token "" |
            Should -Be "nothing changes"
    }

    It "returns the original message when message is empty" {
        Get-RedactedMessage -Message "" -Token "abc123" |
            Should -Be ""
    }

    It "returns null when message is null" {
        Get-RedactedMessage -Message $null -Token "abc123" |
            Should -BeNullOrEmpty
    }

    It "leaves message unchanged when token is not present" {
        Get-RedactedMessage -Message "safe message" -Token "abc123" |
            Should -Be "safe message"
    }

    It "treats token text literally rather than as regex" {
        Get-RedactedMessage -Message "token a.b[c] leaked" -Token "a.b[c]" |
            Should -Be "token [REDACTED_TOKEN] leaked"
    }
}

BeforeAll {
    # Extract and run the function definition only
    $scriptContent = Get-Content -Path "tools/export_ha_nuisance_evidence.ps1" -Raw
    $ast = [System.Management.Automation.Language.Parser]::ParseInput($scriptContent, [ref]$null, [ref]$null)
    $functionAst = $ast.FindAll({$args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst]}, $true) | Where-Object { $_.Name -eq 'Convert-HistoryResponseToRows' }
    Invoke-Expression $functionAst.Extent.Text
}

Describe "Convert-HistoryResponseToRows" {
    It "returns an empty array when HistoryResponse is null" {
        $result = Convert-HistoryResponseToRows -HistoryResponse $null -Category "test"
        $result.GetType().Name | Should -Be "Object[]"
        $result.Count | Should -Be 0
    }

    It "converts normal state points to rows" {
        $mockResponse = @(
            ,(
                [pscustomobject]@{
                    entity_id = "sensor.test"
                    state = "on"
                    last_changed = "2023-01-01"
                    last_updated = "2023-01-01"
                    context = [pscustomobject]@{
                        id = "1"
                        user_id = "user1"
                        parent_id = "parent1"
                    }
                    attributes = @{ attr1 = "val1" }
                }
            )
        )

        $result = Convert-HistoryResponseToRows -HistoryResponse $mockResponse -Category "test_cat"
        $result.Count | Should -Be 1
        $result[0].entity_id | Should -Be "sensor.test"
        $result[0].category | Should -Be "test_cat"
        $result[0].state | Should -Be "on"
        $result[0].attributes_json | Should -Be '{"attr1":"val1"}'
    }

    It "inherits the previous entity_id from the same series if entity_id is missing" {
        $mockResponse = @(
            ,(
                [pscustomobject]@{
                    entity_id = "sensor.minimal"
                    state = "on"
                    last_changed = "2023-01-01"
                    last_updated = "2023-01-01"
                    context = [pscustomobject]@{
                        id = "1"
                        user_id = "user1"
                        parent_id = "parent1"
                    }
                    attributes = @{}
                },
                [pscustomobject]@{
                    entity_id = $null
                    state = "off"
                    last_changed = "2023-01-02"
                    last_updated = "2023-01-02"
                    context = [pscustomobject]@{
                        id = "2"
                        user_id = "user2"
                        parent_id = "parent2"
                    }
                    attributes = @{}
                }
            )
        )

        $result = Convert-HistoryResponseToRows -HistoryResponse $mockResponse -Category "minimal_cat"
        $result.Count | Should -Be 2
        $result[0].entity_id | Should -Be "sensor.minimal"
        $result[1].entity_id | Should -Be "sensor.minimal"
        $result[1].state | Should -Be "off"
    }

    It "applies the category to every row" {
        $mockResponse = @(
            ,(
                [pscustomobject]@{
                    entity_id = "sensor.test1"
                    state = "on"
                    last_changed = "2023-01-01"
                    last_updated = "2023-01-01"
                    context = [pscustomobject]@{
                        id = "1"
                        user_id = "user1"
                        parent_id = "parent1"
                    }
                    attributes = @{}
                }
            ),
            ,(
                [pscustomobject]@{
                    entity_id = "sensor.test2"
                    state = "off"
                    last_changed = "2023-01-01"
                    last_updated = "2023-01-01"
                    context = [pscustomobject]@{
                        id = "2"
                        user_id = "user2"
                        parent_id = "parent2"
                    }
                    attributes = @{}
                }
            )
        )

        $result = Convert-HistoryResponseToRows -HistoryResponse $mockResponse -Category "shared_cat"
        $result.Count | Should -Be 2
        $result[0].category | Should -Be "shared_cat"
        $result[1].category | Should -Be "shared_cat"
    }
}
