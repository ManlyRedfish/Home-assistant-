Describe "Get-RedactedMessage" {
    BeforeAll {
        . "$PSScriptRoot/export_ha_nuisance_evidence.ps1"
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


Describe "Convert-HistoryResponseToRows" {
    BeforeAll {
        . "$PSScriptRoot/export_ha_nuisance_evidence.ps1"
    }

    It "returns no rows when HistoryResponse is null" {
        $result = @(Convert-HistoryResponseToRows -HistoryResponse $null -Category "test")
        $result.Count | Should -Be 0
    }

    It "returns no rows when HistoryResponse is empty" {
        $result = @(Convert-HistoryResponseToRows -HistoryResponse @() -Category "test")
        $result.Count | Should -Be 0
    }

    It "emits only row objects and no List.Add indexes" {
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

        $result = @(Convert-HistoryResponseToRows -HistoryResponse $mockResponse -Category "test")

        $result.Count | Should -Be 2
        ($result | Where-Object { $_ -is [int] }).Count | Should -Be 0
        $result[0].entity_id | Should -Be "sensor.test"
        $result[1].entity_id | Should -Be "sensor.test"
    }
}
