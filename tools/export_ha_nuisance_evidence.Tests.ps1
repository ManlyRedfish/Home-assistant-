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
